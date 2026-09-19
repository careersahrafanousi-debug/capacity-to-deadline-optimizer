"""
Cleans the scheduling extracts, applies 14 data-quality rules, computes access
metrics, and scores the waitlist.

Waitlist Match Score (0-100):
    35  Same specialty as the open slot
    25  Lead-time urgency - how close the requested-by date is
    20  Time preference matches the slot
    10  Notification opt-in
    10  Reschedule readiness

The weights are analyst judgement, not a fitted model. They are stated here and
in the docs so nobody mistakes them for something they are not.

Run after generate_data.py:  python src/clean_and_score.py
"""

import os

import numpy as np
import pandas as pd

RAW = os.path.join("data", "raw")
CLEAN = os.path.join("data", "clean")
PERIOD_END = pd.Timestamp("2026-06-26")

VALID_STATUS = {"Completed", "Scheduled", "Cancelled", "No Show"}
YES = {"yes", "y", "true", "1"}
NO = {"no", "n", "false", "0"}

exceptions = []


def log(rule, record, severity, desc, action):
    exceptions.append({"Exception_ID": f"EX-{len(exceptions)+1:05d}", "Rule_ID": rule,
                       "Record_ID": record, "Severity": severity, "Description": desc,
                       "Action_Taken": action})


def norm_yn(v):
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in YES:
        return "Yes"
    if s in NO:
        return "No"
    return None


def clean_appointments():
    df = pd.read_csv(os.path.join(RAW, "appointments_raw.csv"))
    n_in = len(df)

    # DQ-01 appointment ID must be unique
    for aid in df[df.duplicated("Appointment_ID", keep="first")]["Appointment_ID"]:
        log("DQ-01", aid, "High", "Duplicate Appointment_ID.", "First occurrence retained")
    df = df.drop_duplicates("Appointment_ID", keep="first").copy()

    # DQ-02 specialty must normalize to an approved value
    valid_spec = set(pd.read_csv(os.path.join(RAW, "dim_specialty.csv"))["Specialty"])
    df["Specialty"] = df["Specialty"].astype(str).str.strip().str.title()
    df["Specialty"] = df["Specialty"].replace({"Nan": None})
    bad = df[~df["Specialty"].isin(valid_spec)]
    for aid in bad["Appointment_ID"]:
        log("DQ-02", aid, "Critical", "Specialty could not be mapped to an approved value.",
            "Excluded from reporting")
    df = df[df["Specialty"].isin(valid_spec)].copy()

    # DQ-03 status must be an approved value
    bad = df[~df["Status"].isin(VALID_STATUS)]
    for aid, st in zip(bad["Appointment_ID"], bad["Status"]):
        log("DQ-03", aid, "Critical", f"Unrecognized status value '{st}'.",
            "Excluded from reporting")
    df = df[df["Status"].isin(VALID_STATUS)].copy()

    # DQ-04 appointment datetime required
    df["Appointment_DateTime"] = pd.to_datetime(df["Appointment_DateTime"], errors="coerce")
    for aid in df[df["Appointment_DateTime"].isna()]["Appointment_ID"]:
        log("DQ-04", aid, "Critical", "Appointment_DateTime missing or unparseable.",
            "Excluded from reporting")
    df = df[df["Appointment_DateTime"].notna()].copy()

    df["Request_Date"] = pd.to_datetime(df["Request_Date"], errors="coerce")
    df["Cancellation_Date"] = pd.to_datetime(df["Cancellation_Date"], errors="coerce")

    # DQ-05 appointment must not precede the request
    bad = df[df["Appointment_DateTime"].dt.normalize() < df["Request_Date"]]
    for aid in bad["Appointment_ID"]:
        log("DQ-05", aid, "Critical", "Appointment date precedes the request date.",
            "Excluded from reporting")
    df = df[~df["Appointment_ID"].isin(bad["Appointment_ID"])].copy()

    # DQ-06 cancelled appointments need a cancellation date
    bad = df[(df["Status"] == "Cancelled") & (df["Cancellation_Date"].isna())]
    for aid in bad["Appointment_ID"]:
        log("DQ-06", aid, "High",
            "Cancelled with no cancellation date; fill window cannot be calculated.",
            "Retained, excluded from fill-opportunity analysis")

    # DQ-07 cancellation date must fall between request and appointment
    mask = df["Cancellation_Date"].notna() & (
        (df["Cancellation_Date"] < df["Request_Date"]) |
        (df["Cancellation_Date"] > df["Appointment_DateTime"]))
    for aid in df.loc[mask, "Appointment_ID"]:
        log("DQ-07", aid, "High", "Cancellation date outside the request-to-appointment window.",
            "Cancellation date nulled, record retained")
    df.loc[mask, "Cancellation_Date"] = pd.NaT

    # DQ-08 cancellation reason expected when cancelled
    bad = df[(df["Status"] == "Cancelled") & (df["Cancellation_Reason"].isna())]
    for aid in bad["Appointment_ID"]:
        log("DQ-08", aid, "Low", "Cancellation reason not recorded.", "Retained as Unspecified")
    df.loc[(df["Status"] == "Cancelled") & (df["Cancellation_Reason"].isna()),
           "Cancellation_Reason"] = "Unspecified"

    # DQ-09 reminder flag must normalize to Yes/No
    raw_reminder = df["Reminder_Sent"].copy()
    df["Reminder_Sent"] = df["Reminder_Sent"].map(norm_yn)
    changed = df.loc[(raw_reminder.astype(str) != df["Reminder_Sent"].astype(str)) &
                     df["Reminder_Sent"].notna(), "Appointment_ID"]
    for aid in changed:
        log("DQ-09", aid, "Medium", "Reminder_Sent used a non-standard value.",
            "Normalized to Yes/No")
    for aid in df[df["Reminder_Sent"].isna()]["Appointment_ID"]:
        log("DQ-09", aid, "High", "Reminder_Sent could not be interpreted.",
            "Set to Unknown, excluded from reminder comparison")
    df["Reminder_Sent"] = df["Reminder_Sent"].fillna("Unknown")

    # DQ-10 reschedule flag must normalize
    df["Rescheduled_Flag"] = df["Rescheduled_Flag"].map(norm_yn).fillna("Unknown")

    # DQ-11 slot duration within a plausible range
    bad = df[~df["Slot_Duration_Minutes"].between(10, 90)]
    for aid in bad["Appointment_ID"]:
        log("DQ-11", aid, "Medium", "Slot duration outside the expected 10-90 minute range.",
            "Retained, flagged")

    # DQ-12 provider must exist in reference data
    valid_prov = set(pd.read_csv(os.path.join(RAW, "dim_provider.csv"))["Provider_ID"])
    bad = df[~df["Provider_ID"].isin(valid_prov)]
    for aid in bad["Appointment_ID"]:
        log("DQ-12", aid, "High", "Provider_ID not found in provider reference data.",
            "Retained, excluded from provider analysis")

    # derived fields
    df["Lead_Time_Days"] = (df["Appointment_DateTime"].dt.normalize()
                            - df["Request_Date"]).dt.days
    df["Cancel_Notice_Days"] = (df["Appointment_DateTime"].dt.normalize()
                                - df["Cancellation_Date"]).dt.days
    # a cancellation with 3 or more days notice is realistically refillable
    df["Refillable"] = np.where(
        (df["Status"] == "Cancelled") & (df["Cancel_Notice_Days"] >= 3), "Yes", "No")
    df["Appointment_Date"] = df["Appointment_DateTime"].dt.date.astype(str)
    df["Appointment_Hour"] = df["Appointment_DateTime"].dt.hour
    df["Time_Block"] = np.where(df["Appointment_Hour"] < 12, "Morning", "Afternoon")

    spec = pd.read_csv(os.path.join(RAW, "dim_specialty.csv"))
    df = df.merge(spec, on="Specialty", how="left")
    df["Lead_Time_Within_Standard"] = np.where(
        df["Lead_Time_Days"] <= df["Target_Lead_Time_Days"], "Yes", "No")

    return df, n_in


def clean_waitlist():
    df = pd.read_csv(os.path.join(RAW, "waitlist_raw.csv"))
    n_in = len(df)

    valid_spec = set(pd.read_csv(os.path.join(RAW, "dim_specialty.csv"))["Specialty"])

    # DQ-13 waitlist specialty required
    bad = df[~df["Specialty"].isin(valid_spec)]
    for wid in bad["Waitlist_ID"]:
        log("DQ-13", wid, "Critical", "Waitlist specialty missing or invalid.",
            "Excluded from reporting")
    df = df[df["Specialty"].isin(valid_spec)].copy()

    df["Date_Added"] = pd.to_datetime(df["Date_Added"], errors="coerce")
    df["Requested_By_Date"] = pd.to_datetime(df["Requested_By_Date"], errors="coerce")
    df["Offered_Slot_Date"] = pd.to_datetime(df["Offered_Slot_Date"], errors="coerce")

    # DQ-14 requested-by date must not precede the date added
    bad = df[df["Requested_By_Date"] < df["Date_Added"]]
    for wid in bad["Waitlist_ID"]:
        log("DQ-14", wid, "High", "Requested_By_Date precedes Date_Added.",
            "Requested_By_Date nulled; urgency scored as unknown")
    df.loc[df["Requested_By_Date"] < df["Date_Added"], "Requested_By_Date"] = pd.NaT

    # DQ-15 offer accepted with no offer recorded
    bad = df[(df["Offer_Accepted"] == "Yes") & (df["Offered_Slot_Date"].isna())]
    for wid in bad["Waitlist_ID"]:
        log("DQ-15", wid, "High", "Offer_Accepted is Yes but no offered slot date exists.",
            "Offer_Accepted reset to Unknown")
    df.loc[(df["Offer_Accepted"] == "Yes") & (df["Offered_Slot_Date"].isna()),
           "Offer_Accepted"] = "Unknown"

    df["Notification_Opt_In"] = df["Notification_Opt_In"].map(norm_yn).fillna("Unknown")
    df["Days_To_Requested_By"] = (df["Requested_By_Date"] - PERIOD_END).dt.days
    return df, n_in


def score_waitlist(wl, appts):
    """Waitlist Match Score - which waiting patient should be called first when a
    slot opens. Scored against the specialty's own open-slot picture rather than
    one specific slot, so the output is a ranked call list."""

    # what does the supply side look like per specialty and time block?
    refillable = appts[(appts["Status"] == "Cancelled") & (appts["Refillable"] == "Yes")]
    supply = refillable.groupby(["Specialty", "Time_Block"]).size().rename("Open_Slots")
    supply_spec = refillable.groupby("Specialty").size().rename("Spec_Open_Slots")
    dominant_block = (refillable.groupby(["Specialty", "Time_Block"]).size()
                      .reset_index(name="n")
                      .sort_values("n", ascending=False)
                      .drop_duplicates("Specialty")
                      .set_index("Specialty")["Time_Block"])

    wl = wl.merge(supply_spec, left_on="Specialty", right_index=True, how="left")
    wl["Spec_Open_Slots"] = wl["Spec_Open_Slots"].fillna(0)
    wl["Dominant_Open_Block"] = wl["Specialty"].map(dominant_block)

    # 35 - specialty match, scaled by how much refillable supply that specialty
    # actually has per waiting patient. A flat 35 for "same specialty" would give
    # every row the same points and tell the scheduler nothing, so the component
    # measures matchability rather than mere eligibility.
    demand = wl.groupby("Specialty")["Waitlist_ID"].transform("count")
    wl["Slots_Per_Waiting_Patient"] = (wl["Spec_Open_Slots"] / demand).round(3)
    r = wl["Slots_Per_Waiting_Patient"]
    s_spec = np.select([r >= 0.35, r >= 0.28, r >= 0.22, r > 0], [35, 26, 17, 8], default=0)

    # 25 - lead-time urgency, graded by how close the requested-by date is
    d = wl["Days_To_Requested_By"]
    s_urgency = np.select(
        [d.isna(), d <= 0, d <= 7, d <= 21, d <= 45],
        [8, 25, 22, 16, 9], default=4)

    # 20 - time preference match
    s_time = np.where(
        wl["Preferred_Time"] == "No preference", 20,
        np.where(wl["Preferred_Time"] == wl["Dominant_Open_Block"], 20, 6))

    # 10 - notification opt-in, because you cannot fill a slot you cannot offer
    s_notify = np.where(wl["Notification_Opt_In"] == "Yes", 10, 0)

    # 10 - reschedule readiness: short travel and an offer history means a fast yes
    ready = (wl["Travel_Category"] == "Under 15 miles").astype(int) \
        + (wl["Offer_Accepted"] == "Yes").astype(int) \
        + (wl["Offered_Slot_Date"].notna()).astype(int)
    s_ready = np.select([ready >= 2, ready == 1], [10, 5], default=0)

    wl["Score_Specialty"] = s_spec
    wl["Score_Urgency"] = s_urgency
    wl["Score_Time_Match"] = s_time
    wl["Score_Notification"] = s_notify
    wl["Score_Reschedule_Ready"] = s_ready
    wl["Waitlist_Match_Score"] = (s_spec + s_urgency + s_time + s_notify + s_ready)

    wl["Match_Priority"] = pd.cut(wl["Waitlist_Match_Score"],
                                  bins=[-1, 49, 64, 79, 100],
                                  labels=["Low", "Moderate", "High", "Critical"])
    return wl


def simulate_fill(appts, rates=(0.30, 0.50, 0.70)):
    """If we filled X% of refillable cancellations, how much access do we recover?
    Expressed as slots and as days of lead time, never as dollars."""
    refill = appts[(appts["Status"] == "Cancelled") & (appts["Refillable"] == "Yes")]
    n_refill = len(refill)
    completed = (appts["Status"] == "Completed").sum()
    rows = []
    for r in rates:
        filled = int(round(n_refill * r))
        rows.append({
            "Fill_Rate_Modeled": f"{int(r*100)}%",
            "Refillable_Cancellations": n_refill,
            "Slots_Recovered": filled,
            "Recovered_As_Pct_Of_Completed": round(100.0 * filled / completed, 2),
            "Note": "Modeled opportunity, subject to validation with scheduling staff",
        })
    return pd.DataFrame(rows), n_refill


def main():
    os.makedirs(CLEAN, exist_ok=True)
    appts, n_appt_in = clean_appointments()
    wl, n_wl_in = clean_waitlist()
    wl = score_waitlist(wl, appts)
    sim, n_refill = simulate_fill(appts)

    ex = pd.DataFrame(exceptions)
    appts.to_csv(os.path.join(CLEAN, "appointments.csv"), index=False)
    wl.to_csv(os.path.join(CLEAN, "waitlist_scored.csv"), index=False)
    sim.to_csv(os.path.join(CLEAN, "fill_simulation.csv"), index=False)
    ex.to_csv(os.path.join(CLEAN, "dq_exceptions.csv"), index=False)

    blocked = (ex["Action_Taken"] == "Excluded from reporting").sum()
    print(f"appointments in:   {n_appt_in}")
    print(f"appointments out:  {len(appts)}")
    print(f"waitlist in:       {n_wl_in}")
    print(f"waitlist out:      {len(wl)}")
    print(f"exceptions:        {len(ex)}  (excluded {blocked})")
    print(f"Data Quality Score: {100*(1-blocked/n_appt_in):.2f}%")
    print()
    print("Status mix:")
    print(appts["Status"].value_counts().to_string())
    print()
    print("No-show rate by reminder:")
    print((appts[appts["Status"].isin(["Completed", "No Show"])]
           .groupby("Reminder_Sent")["Status"]
           .apply(lambda s: round(100*(s == "No Show").mean(), 2)).to_string()))
    print()
    print("Median lead time by visit type:")
    print(appts.groupby("Visit_Type")["Lead_Time_Days"].median().to_string())
    print()
    print(f"Refillable cancellations: {n_refill}")
    print(sim.to_string(index=False))
    print()
    print("Waitlist match priority:")
    print(wl["Match_Priority"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
