# UAT Test Cases — Capacity-to-Deadline Optimizer

Run the three scripts in order against seed 5150, then execute
`sql/06_sql_analysis.sql`. Query numbers below refer to that file.

| ID | Story | Test | Expected | Result |
|---|---|---|---|---|
| UAT-01 | US-01 | Access by specialty against its own standard | Query 3 returns 6 rows, worst first: Orthopedics 57.4%, Cardiology 58.1%, Gastroenterology 59.3%, Endocrinology 59.8%, Pulmonology 59.8%, Neurology 60.9% | Pass |
| UAT-02 | US-02 | Lead time by visit type | Query 2: New Patient 44.2 days / 31.4% within standard; Follow-Up 26.3 / 64.3%; Established 23.1 / 73.2% | Pass |
| UAT-03 | US-03 | Ranked queue with visible components | Query 12 returns 50 rows sorted by score descending; all five component columns present; top row scores 100 | Pass |
| UAT-04 | US-04 | Cancellations by notice band | Query 7: no date 82, same day 293, 1-2 days 371, 3-7 days 393, over 7 days 114 — sums to 1,253 cancellations | Pass |
| UAT-05 | US-05 | Refillable supply by specialty and block | Query 8 returns 12 rows; morning exceeds afternoon in every specialty; total 507 | Pass |
| UAT-06 | US-06 | Reminder effect, controlled for visit type | Query 4: 5.27% with reminder vs 15.68% without. Query 5 confirms within every visit type: Established 4.44 vs 13.2, Follow-Up 5.02 vs 13.49, New Patient 7.11 vs 22.96 | Pass |
| UAT-07 | US-07 | No-show rate by lead-time band | Query 6: 6.32%, 7.93%, 9.34%, 13.79% — monotonic increase | Pass |
| UAT-08 | US-08 | Booked vs realized utilization per provider | Query 10 returns 22 providers; PRV-019 booked 72.0% / realized 50.6%; PRV-021 booked 100.0% / realized 71.2%. Query 11 gives pulmonology spread 20.6pp | Pass |
| UAT-09 | US-09 | Fill simulation in slots, not dollars | Query 16: 30% → 152 slots (1.62%), 50% → 254 (2.70%), 70% → 355 (3.78%); Note column present on every row; no currency anywhere in the output | Pass |
| UAT-10 | US-10 | Waitlist past requested-by date | Query 14: 946 of 1,786 overall (53.0%); endocrinology worst at 58.0% | Pass |
| UAT-11 | US-11 | Exception log reconciles | Query 18 sums to 376 exceptions; excluded actions total 63; 14,048 − 97 appointment removals = 13,951, and 1,800 − 14 = 1,786 | Pass |
| UAT-12 | US-12 | Opt-in vs acceptance reported honestly | Query 15: opt-in 54.0% acceptance, non-opt-in 55.9%. Reported as a null result rather than suppressed | Pass |

## Pipeline reconciliation

| Check | Expected | Actual |
|---|---|---|
| Raw appointment rows | 14,000 generated + 48 duplicates | 14,048 |
| Duplicates removed (DQ-01) | 48 | 48 |
| Excluded: bad status (DQ-03) | 18 | 18 |
| Excluded: missing datetime (DQ-04) | 31 | 31 |
| Appointments to reporting | 14,048 − 48 − 18 − 31 | 13,951 |
| Waitlist raw | 1,800 | 1,800 |
| Excluded: blank specialty (DQ-13) | 14 | 14 |
| Waitlist to reporting | 1,786 | 1,786 |
| Data Quality Score | (1 − 63/14,048) × 100 | 99.55% |
| Status mix | Completed + Scheduled + Cancelled + No Show | 9,400 + 2,464 + 1,253 + 834 = 13,951 |

The status mix summing exactly to the reporting row count is the check that matters — no record
fell out of the pipeline silently.

## Defects raised

**D-01 — Notification opt-in carries 10 points but does not predict acceptance.** Query 15
shows 54.0% acceptance among opt-in patients against 55.9% among non-opt-in. The score component
was justified on speed of contact, not likelihood of a yes, but the weight was never tested and
the data does not support it as an intent signal. Open. The to-be process map adds the monthly
weight review that would resolve it; the README and dashboard both surface the null result
rather than hiding it.

**D-02 — 60 cancellations are unassessable for refill.** DQ-06 catches cancelled appointments
with no cancellation date. These records are excluded from the refillable population and are not
counted as unrefillable either, so the 507 figure is a floor, not a total. Root cause is a
non-mandatory form field, not a pipeline bug. Raised as recommendation 3.

**D-03 — Access compliance is measured against `Target_Lead_Time_Days`, not `Access_Standard`.**
`dim_specialty` carries both, and they differ (Orthopedics targets 19 days against a 14-day
published standard). The pipeline uses the target. Compliance measured against the published
standard would be materially worse. This is a definitional ambiguity that a real engagement
would have to settle with the access manager before publishing anything. Documented, not
resolved.

**D-04 — Provider capacity is derived from the appointment table.** `Available_Slots` is
back-calculated from booked slots and each provider's target utilization, so capacity and demand
cannot disagree. This makes any reconciliation between the two tables circular and trivially
passing, which is why no such rule exists (see the quality rules document). In a real system
capacity would be an independent source and that check would be the first thing to add.
