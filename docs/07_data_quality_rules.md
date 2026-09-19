# Data Quality Rules — Capacity-to-Deadline Optimizer

Fifteen rules in `src/clean_and_score.py`. Critical failures are excluded from reporting and
logged. Nothing is silently corrected: every normalization is recorded as an exception with the
action taken.

| Severity | Effect |
|---|---|
| Critical | Record excluded from reporting |
| High | Record retained but excluded from the affected analysis, or a field nulled |
| Medium | Value normalized, record retained |
| Low | Logged for monitoring |

## Rules

| ID | Rule | Severity | Action | Count this run |
|---|---|---|---|---|
| DQ-01 | Appointment_ID must be unique | High | First occurrence retained | 48 |
| DQ-02 | Specialty must normalize to an approved value | Critical | Excluded | 0 |
| DQ-03 | Status must be Completed, Scheduled, Cancelled, or No Show | Critical | Excluded | 18 |
| DQ-04 | Appointment_DateTime must be present and parseable | Critical | Excluded | 31 |
| DQ-05 | Appointment date must not precede the request date | Critical | Excluded | 0 |
| DQ-06 | Cancelled appointments must have a cancellation date | High | Retained, excluded from fill analysis | 60 |
| DQ-07 | Cancellation date must fall between request and appointment | High | Date nulled, record retained | 22 |
| DQ-08 | Cancellation reason expected when cancelled | Low | Set to Unspecified | 0 |
| DQ-09 | Reminder_Sent must normalize to Yes or No | Medium / High | Normalized, or set Unknown | 138 |
| DQ-10 | Rescheduled_Flag must normalize to Yes or No | Medium | Normalized | 0 |
| DQ-11 | Slot duration must be 10-90 minutes | Medium | Retained, flagged | 0 |
| DQ-12 | Provider_ID must exist in dim_provider | High | Retained, excluded from provider analysis | 0 |
| DQ-13 | Waitlist specialty must be present and valid | Critical | Excluded | 14 |
| DQ-14 | Requested_By_Date must not precede Date_Added | High | Nulled, urgency scored as unknown | 25 |
| DQ-15 | Offer_Accepted requires an offered slot date | High | Reset to Unknown | 20 |

**Total 376 exceptions. 63 records excluded (31 + 18 appointments, 14 waitlist).**

## Data Quality Score

```
Data Quality Score = (1 - Records excluded / Records evaluated) x 100
                   = (1 - 63 / 14,048) x 100 = 99.55%
```

| Measure | Value |
|---|---|
| Appointment rows in | 14,048 |
| Appointment rows to reporting | 13,951 |
| Waitlist rows in | 1,800 |
| Waitlist rows to reporting | 1,786 |
| Exceptions logged | 376 |
| Records excluded | 63 |
| **Data Quality Score** | **99.55%** |

## DQ-02 returned zero, and that is worth explaining

The generator injects 95 rows with lowercase, space-prefixed specialty names. All 95 normalize
cleanly via trim and title-case before the rule is evaluated, so the rule finds nothing to
exclude. The mess was real; the normalization handled it. The rule stays because the next
unexpected spelling will not normalize, and that is precisely when you want it firing.

The same logic applies to DQ-05, DQ-08, DQ-10, DQ-11, and DQ-12, which are all zero on this
dataset. They are guards against source changes, not decoration.

## The DQ-06 rule has a direct operational cost

60 cancelled appointments have no cancellation date. Those records cannot be assessed for
refillability at all — they are not counted in the 507 refillable slots, and they are not
counted as unrefillable either. They are simply invisible to the fill opportunity. This is the
clearest case in the project of a data-entry gap destroying operational value, and it is the
basis for recommendation 3 in the README.

## Rules deliberately not implemented

- **No outlier rule on lead time.** A 226-day lead time is extreme but not wrong; excluding it
  would erase exactly the access failure the project exists to find.
- **No imputation of missing cancellation dates.** Any guess would manufacture or destroy a fill
  opportunity. Better to report 60 records as unassessable.
- **No cross-checking of appointment counts against provider_capacity.** Capacity is derived
  from appointments in this build, so the check would be circular and would pass trivially. In a
  real system with independent capacity data this would be rule 16.
