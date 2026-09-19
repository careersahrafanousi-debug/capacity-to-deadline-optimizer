"""
Frontier Specialty Care Network (fictional) - synthetic scheduling data.

Three tables:
  appointments      - every requested and scheduled visit
  waitlist          - patients waiting for an earlier slot
  provider_capacity - daily slot supply and consumption per provider

Patterns deliberately built in, because a scheduling dataset with no structure
teaches nothing:
  - new patients wait materially longer than established patients
  - cancellation rates vary by specialty
  - appointments with a reminder sent have lower no-show rates
  - a meaningful share of cancellations happen late, leaving slots unfilled
  - provider utilization is uneven within the same specialty

Some dirty records are injected on purpose so the cleaning step has work to do.

Run:  python src/generate_data.py
"""

import os
import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

SEED = 5150
N_APPTS = 14000
N_WAITLIST = 1800
START = date(2026, 1, 5)
END = date(2026, 6, 26)
RAW = os.path.join("data", "raw")

SPECIALTIES = {
    # specialty: (base lead time days, cancellation rate, no-show base, slot minutes)
    "Cardiology":      (24, 0.11, 0.07, 30),
    "Endocrinology":   (38, 0.13, 0.09, 30),
    "Orthopedics":     (19, 0.09, 0.06, 20),
    "Neurology":       (41, 0.14, 0.10, 40),
    "Gastroenterology": (29, 0.12, 0.08, 30),
    "Pulmonology":     (26, 0.10, 0.08, 30),
}

CANCEL_REASONS = ["Patient request", "Patient illness", "Provider unavailable",
                  "Transportation", "Insurance issue", "No reason given"]

TRAVEL = ["Under 15 miles", "15 to 40 miles", "Over 40 miles"]
TIME_PREF = ["Morning", "Afternoon", "No preference"]


def build_providers():
    rows = []
    pid = 1
    for spec in SPECIALTIES:
        for _ in range(random.randint(3, 5)):
            rows.append({
                "Provider_ID": f"PRV-{pid:03d}",
                "Specialty": spec,
                # daily slot supply differs by provider, which is where the
                # utilization spread comes from
                "Daily_Slots": random.choice([8, 10, 12, 14, 16]),
                # some providers are simply booked harder than their peers
                "Demand_Factor": round(random.uniform(0.72, 1.06), 2),
            })
            pid += 1
    return pd.DataFrame(rows)


def build_appointments(providers):
    rows = []
    span = (END - START).days
    for i in range(1, N_APPTS + 1):
        prov = providers.sample(1, weights=providers["Daily_Slots"]).iloc[0]
        spec = prov["Specialty"]
        base_lead, cancel_p, noshow_base, slot_min = SPECIALTIES[spec]

        visit_type = random.choices(["New Patient", "Established", "Follow-Up"],
                                    weights=[0.28, 0.44, 0.28])[0]
        # new patients wait longer - the core access finding
        lead_mult = {"New Patient": 1.55, "Established": 0.82, "Follow-Up": 0.95}[visit_type]
        lead = max(1, int(np.random.gamma(3.2, base_lead * lead_mult / 3.2)))

        request_date = START + timedelta(days=random.randint(0, span))
        appt_dt = datetime.combine(request_date + timedelta(days=lead), datetime.min.time())
        hour = random.choices([8, 9, 10, 11, 13, 14, 15, 16],
                              weights=[.14, .16, .15, .12, .11, .12, .11, .09])[0]
        appt_dt = appt_dt.replace(hour=hour, minute=random.choice([0, 15, 30, 45]))

        reminder = "Yes" if random.random() < 0.72 else "No"
        # reminders roughly halve the no-show rate in this dataset
        noshow_p = noshow_base * (0.55 if reminder == "Yes" else 1.6)
        if visit_type == "New Patient":
            noshow_p *= 1.35          # new patients no-show more
        if lead > base_lead * 1.5:
            noshow_p *= 1.25          # long waits erode show rates

        rescheduled = "Yes" if random.random() < 0.17 else "No"
        if rescheduled == "Yes":
            noshow_p *= 1.15

        status, cancel_date, cancel_reason = "Completed", None, None
        r = random.random()
        if appt_dt.date() > END:
            status = "Scheduled"
        elif r < cancel_p:
            status = "Cancelled"
            # how late the cancellation lands decides whether the slot is fillable
            days_before = random.choices([0, 1, 2, 3, 7, 14],
                                         weights=[.24, .18, .13, .15, .18, .12])[0]
            cancel_date = (appt_dt - timedelta(days=days_before)).date()
            if cancel_date < request_date:
                cancel_date = request_date
            cancel_reason = random.choice(CANCEL_REASONS)
        elif r < cancel_p + noshow_p:
            status = "No Show"

        rows.append({
            "Appointment_ID": f"APT-{i:06d}",
            "Patient_Group": random.choice(["Group A", "Group B", "Group C", "Group D"]),
            "Specialty": spec,
            "Provider_ID": prov["Provider_ID"],
            "Request_Date": request_date.isoformat(),
            "Appointment_DateTime": appt_dt.strftime("%Y-%m-%d %H:%M"),
            "Visit_Type": visit_type,
            "Status": status,
            "Cancellation_Date": cancel_date.isoformat() if cancel_date else None,
            "Cancellation_Reason": cancel_reason,
            "Reminder_Sent": reminder,
            "Slot_Duration_Minutes": slot_min,
            "Rescheduled_Flag": rescheduled,
        })
    return pd.DataFrame(rows)


def build_waitlist(appts):
    rows = []
    for i in range(1, N_WAITLIST + 1):
        spec = random.choice(list(SPECIALTIES))
        base_lead = SPECIALTIES[spec][0]
        # the live waitlist is weighted toward recent additions - older entries
        # have mostly been scheduled or have dropped off
        added = END - timedelta(days=int(np.random.gamma(2.0, 22.0)) + 1)
        if added < START:
            added = START + timedelta(days=random.randint(0, 20))
        # how soon the patient actually needs to be seen
        requested_by = added + timedelta(days=random.choice([7, 14, 21, 30, 45, 60, 90]))
        offered = None
        accepted = "No"
        if random.random() < 0.34:
            offered = (added + timedelta(days=random.randint(1, 30))).isoformat()
            accepted = "Yes" if random.random() < 0.58 else "No"
        rows.append({
            "Waitlist_ID": f"WL-{i:05d}",
            "Patient_Group": random.choice(["Group A", "Group B", "Group C", "Group D"]),
            "Specialty": spec,
            "Date_Added": added.isoformat(),
            "Requested_By_Date": requested_by.isoformat(),
            "Preferred_Time": random.choices(TIME_PREF, weights=[.45, .33, .22])[0],
            "Travel_Category": random.choices(TRAVEL, weights=[.52, .33, .15])[0],
            "Notification_Opt_In": "Yes" if random.random() < 0.63 else "No",
            "Offered_Slot_Date": offered,
            "Offer_Accepted": accepted,
            "Days_Waiting": (END - added).days,
            "Current_Lead_Time_Estimate": base_lead,
        })
    return pd.DataFrame(rows)


def build_capacity(providers, appts):
    """Derived from the appointment table so supply and demand actually agree,
    then given an independent no-show/cancel view per day."""
    appts = appts.copy()
    appts["Appt_Date"] = pd.to_datetime(appts["Appointment_DateTime"]).dt.date
    grouped = appts.groupby(["Provider_ID", "Appt_Date", "Status"]).size().unstack(fill_value=0)

    rows = []
    for (pid, day), g in grouped.groupby(level=[0, 1]):
        prov = providers[providers["Provider_ID"] == pid].iloc[0]
        row = g.iloc[0]
        booked = int(row.sum())
        # Available slots are derived so that each provider lands near its own
        # target booked-utilization. Demand_Factor is the target: a provider at
        # 0.72 leaves a quarter of the session unbooked, one at 1.06 is clamped
        # to 0.95 because you cannot book more than you open.
        target_util = min(0.95, max(0.55, prov["Demand_Factor"]))
        available = max(booked, int(round(booked / target_util)))
        rows.append({
            "Provider_ID": pid,
            "Date": day.isoformat(),
            "Specialty": prov["Specialty"],
            "Available_Slots": available,
            "Booked_Slots": booked,
            "Completed_Slots": int(row.get("Completed", 0)),
            "Cancelled_Slots": int(row.get("Cancelled", 0)),
            "No_Show_Slots": int(row.get("No Show", 0)),
        })
    return pd.DataFrame(rows).sort_values(["Date", "Provider_ID"]).reset_index(drop=True)


def dirty(appts, waitlist):
    """Inject realistic mess. The cleaning step has to find all of it."""
    # duplicate appointment rows, as happens when a booking is re-entered
    dupes = appts.sample(48, random_state=11)
    appts = pd.concat([appts, dupes], ignore_index=True)

    # Yes/N/y variants in the reminder flag
    idx = appts.sample(140, random_state=12).index
    appts.loc[idx, "Reminder_Sent"] = appts.loc[idx, "Reminder_Sent"].map(
        {"Yes": random.choice(["Y", "yes", "YES"]), "No": random.choice(["N", "no"])})

    # specialty spelling and whitespace drift
    idx = appts.sample(95, random_state=13).index
    appts.loc[idx, "Specialty"] = " " + appts.loc[idx, "Specialty"].str.lower()

    # cancelled with no cancellation date - breaks the fill-window calculation
    cancelled = appts[appts["Status"] == "Cancelled"].sample(60, random_state=14).index
    appts.loc[cancelled, "Cancellation_Date"] = None

    # cancellation recorded before the request was even made
    bad = appts[appts["Cancellation_Date"].notna()].sample(22, random_state=15).index
    appts.loc[bad, "Cancellation_Date"] = "2025-12-01"

    # appointment datetime blank
    idx = appts.sample(31, random_state=16).index
    appts.loc[idx, "Appointment_DateTime"] = None

    # a status value nobody documented
    idx = appts.sample(18, random_state=17).index
    appts.loc[idx, "Status"] = "PENDING-CONFIRM"

    # waitlist: requested-by date before the date added
    idx = waitlist.sample(25, random_state=18).index
    waitlist.loc[idx, "Requested_By_Date"] = "2025-11-15"

    # waitlist: blank specialty
    idx = waitlist.sample(14, random_state=19).index
    waitlist.loc[idx, "Specialty"] = None

    # waitlist: offer accepted recorded with no offer made
    idx = waitlist[waitlist["Offered_Slot_Date"].isna()].sample(20, random_state=20).index
    waitlist.loc[idx, "Offer_Accepted"] = "Yes"

    return appts.sample(frac=1, random_state=21).reset_index(drop=True), waitlist


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    os.makedirs(RAW, exist_ok=True)

    providers = build_providers()
    appts = build_appointments(providers)
    waitlist = build_waitlist(appts)
    capacity = build_capacity(providers, appts)
    appts_dirty, waitlist_dirty = dirty(appts, waitlist)

    dates = pd.date_range(START, END, freq="D")
    dim_date = pd.DataFrame({
        "Date": dates.strftime("%Y-%m-%d"),
        "Year": dates.year, "Month": dates.month,
        "Month_Name": dates.strftime("%B"), "Quarter": dates.quarter,
        "Week_Of_Year": dates.isocalendar().week.values,
        "Day_Name": dates.strftime("%A"),
        "Is_Weekend": np.where(dates.dayofweek >= 5, "Yes", "No"),
    })

    dim_spec = pd.DataFrame([
        {"Specialty": s, "Target_Lead_Time_Days": t,
         "Access_Standard": "14 days" if t <= 20 else ("21 days" if t <= 30 else "30 days")}
        for s, (t, _, _, _) in SPECIALTIES.items()])

    appts_dirty.to_csv(os.path.join(RAW, "appointments_raw.csv"), index=False)
    waitlist_dirty.to_csv(os.path.join(RAW, "waitlist_raw.csv"), index=False)
    capacity.to_csv(os.path.join(RAW, "provider_capacity.csv"), index=False)
    providers.to_csv(os.path.join(RAW, "dim_provider.csv"), index=False)
    dim_spec.to_csv(os.path.join(RAW, "dim_specialty.csv"), index=False)
    dim_date.to_csv(os.path.join(RAW, "dim_date.csv"), index=False)

    with pd.ExcelWriter(os.path.join(RAW, "04_synthetic_raw_data.xlsx")) as xl:
        appts_dirty.head(5000).to_excel(xl, sheet_name="appointments", index=False)
        waitlist_dirty.to_excel(xl, sheet_name="waitlist", index=False)
        capacity.to_excel(xl, sheet_name="provider_capacity", index=False)
        dim_provider = providers
        dim_provider.to_excel(xl, sheet_name="dim_provider", index=False)
        dim_spec.to_excel(xl, sheet_name="dim_specialty", index=False)

    print(f"providers:        {len(providers)}")
    print(f"appointments:     {len(appts_dirty)} rows (48 duplicates injected)")
    print(f"waitlist:         {len(waitlist_dirty)}")
    print(f"capacity rows:    {len(capacity)}")
    print("\nStatus mix before cleaning:")
    print(appts_dirty["Status"].value_counts().to_string())


if __name__ == "__main__":
    main()
