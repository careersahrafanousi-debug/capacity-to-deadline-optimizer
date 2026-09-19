# Data Dictionary — Capacity-to-Deadline Optimizer

Synthetic data, seed 5150. Request dates 2026-01-05 to 2026-06-26.

## appointments (13,951 rows after cleaning, 14,048 raw)

| Field | Type | Description |
|---|---|---|
| Appointment_ID | text | `APT-NNNNNN`. 48 duplicates injected and removed by DQ-01 |
| Patient_Group | text | Group A-D. Deliberately coarse — no patient identity exists in this repo |
| Specialty | text | One of six; free-text drift normalized by DQ-02 |
| Provider_ID | text | FK to dim_provider |
| Request_Date | date | When the appointment was requested |
| Appointment_DateTime | datetime | Scheduled date and time; 31 blanks excluded by DQ-04 |
| Visit_Type | text | New Patient, Established, Follow-Up |
| Status | text | Completed, Scheduled, Cancelled, No Show. 18 `PENDING-CONFIRM` excluded by DQ-03 |
| Cancellation_Date | date | Null unless cancelled; 60 missing on cancelled rows (DQ-06) |
| Cancellation_Reason | text | Six reasons; blanks set to Unspecified by DQ-08 |
| Reminder_Sent | text | Yes / No / Unknown after normalizing `Y`, `yes`, `YES`, `N`, `no` (DQ-09) |
| Slot_Duration_Minutes | int | 20-40 by specialty |
| Rescheduled_Flag | text | Yes / No / Unknown |

### Derived fields

| Field | Type | Derivation |
|---|---|---|
| Lead_Time_Days | int | `Appointment date - Request_Date` |
| Cancel_Notice_Days | int | `Appointment date - Cancellation_Date`; null where the date is missing |
| Refillable | text | Yes when cancelled and notice >= 3 days |
| Appointment_Date | date | Date part of Appointment_DateTime |
| Appointment_Hour | int | Hour 8-16 |
| Time_Block | text | Morning if hour < 12, else Afternoon |
| Target_Lead_Time_Days | int | Joined from dim_specialty |
| Lead_Time_Within_Standard | text | Yes when Lead_Time_Days <= Target_Lead_Time_Days |

Status mix after cleaning: Completed 9,400, Scheduled 2,464, Cancelled 1,253, No Show 834.

## waitlist (1,786 rows after cleaning, 1,800 raw)

| Field | Type | Description |
|---|---|---|
| Waitlist_ID | text | `WL-NNNNN` |
| Patient_Group | text | Group A-D |
| Specialty | text | 14 blanks excluded by DQ-13 |
| Date_Added | date | When the patient joined the waitlist |
| Requested_By_Date | date | When the patient asked to be seen by; 25 invalid values nulled by DQ-14 |
| Preferred_Time | text | Morning, Afternoon, No preference |
| Travel_Category | text | Under 15 miles, 15 to 40 miles, Over 40 miles |
| Notification_Opt_In | text | Yes / No / Unknown |
| Offered_Slot_Date | date | Null where no offer has been made |
| Offer_Accepted | text | Yes / No / Unknown; 20 reset by DQ-15 |
| Days_Waiting | int | Days from Date_Added to period end |
| Current_Lead_Time_Estimate | int | Specialty base lead time at the time of listing |

### Scoring fields

| Field | Type | Description |
|---|---|---|
| Spec_Open_Slots | int | Refillable cancellations in that specialty |
| Slots_Per_Waiting_Patient | float | `Spec_Open_Slots / waiting patients in that specialty` |
| Score_Specialty | int | 35 / 26 / 17 / 8 by slots per waiting patient (0.35, 0.28, 0.22 thresholds) |
| Score_Urgency | int | 25 past due, 22 within 7 days, 16 within 21, 9 within 45, 4 beyond, 8 unknown |
| Score_Time_Match | int | 20 for No preference or a match to the specialty's dominant open block, else 6 |
| Score_Notification | int | 10 when opted in |
| Score_Reschedule_Ready | int | 10 when two or more of: under 15 miles, prior offer, prior acceptance; 5 for one |
| Waitlist_Match_Score | int | Sum of the five components, 0-100 |
| Match_Priority | text | Low 0-49, Moderate 50-64, High 65-79, Critical 80-100 |
| Days_To_Requested_By | int | Negative means already past the requested date |

Score distribution on the current run: mean 66.7, min 27, max 100. Priority counts: Low 197,
Moderate 569, High 704, Critical 316.

## provider_capacity (4,347 rows)

One row per provider per day with at least one appointment.

| Field | Type | Description |
|---|---|---|
| Provider_ID | text | FK to dim_provider |
| Date | date | Session date |
| Specialty | text | Provider's specialty |
| Available_Slots | int | Slots opened. Derived so each provider lands near its own target booked utilization |
| Booked_Slots | int | Slots booked |
| Completed_Slots | int | Visits completed |
| Cancelled_Slots | int | Cancellations |
| No_Show_Slots | int | No-shows |

## dim_specialty (6 rows)

| Specialty | Target lead time | Access standard |
|---|---|---|
| Orthopedics | 19 | 14 days |
| Cardiology | 24 | 21 days |
| Pulmonology | 26 | 21 days |
| Gastroenterology | 29 | 21 days |
| Endocrinology | 38 | 30 days |
| Neurology | 41 | 30 days |

`Target_Lead_Time_Days` is the specialty's typical achievable lead time in the generator;
`Access_Standard` is the commitment the network reports against. Compliance in this project is
measured against `Target_Lead_Time_Days`.

## dim_provider (22 rows)

| Field | Type | Description |
|---|---|---|
| Provider_ID | text | `PRV-NNN` |
| Specialty | text | One of six |
| Daily_Slots | int | 8-16 |
| Demand_Factor | float | Target booked utilization, 0.72-1.06, clamped to 0.95 in capacity derivation |

## dq_exceptions (376 rows)

| Field | Type | Description |
|---|---|---|
| Exception_ID | text | `EX-NNNNN` |
| Rule_ID | text | DQ-01 … DQ-15 |
| Record_ID | text | Appointment or waitlist ID |
| Severity | text | Critical, High, Medium, Low |
| Description | text | What failed |
| Action_Taken | text | Excluded, normalized, nulled, or retained-and-flagged |

## fill_simulation (3 rows)

| Field | Description |
|---|---|
| Fill_Rate_Modeled | 30%, 50%, 70% |
| Refillable_Cancellations | 507 |
| Slots_Recovered | Modeled slots filled |
| Recovered_As_Pct_Of_Completed | Recovered slots as a share of 9,400 completed visits |
| Note | Modeled opportunity, subject to validation with scheduling staff |
