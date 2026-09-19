# Business Requirements — Capacity-to-Deadline Optimizer

## User stories

**US-01** As a patient access manager, I want lead time reported by specialty against that
specialty's own standard so that I am not comparing a 14-day and a 30-day commitment as if they
were the same.
*Acceptance:* one row per specialty with target days, average lead time, and percent within
standard; sorted worst first.

**US-02** As a patient access manager, I want lead time and access compliance broken out by
visit type so that new-patient access is visible.
*Acceptance:* New Patient, Established, and Follow-Up reported separately; blended figure never
shown alone on the overview page.

**US-03** As a scheduling supervisor, I want a ranked queue of waiting patients with the score
broken into its components so that I can see why a patient is ranked where they are.
*Acceptance:* queue sorted by score then days waiting; all five component columns visible; top
50 accessible without filtering.

**US-04** As a scheduling supervisor, I want cancellations classified by notice period so that I
know which are realistically refillable.
*Acceptance:* notice bands from same-day to over seven days, plus an explicit band for
cancellations with no date recorded; refillable population counted.

**US-05** As a specialty clinic lead, I want refillable slots shown by specialty and time block
so that the supply side of the match is concrete.
*Acceptance:* refillable count and average notice days per specialty and morning/afternoon.

**US-06** As an operations leader, I want to know whether reminders change the no-show rate,
controlled for visit type, so that a reminder mandate can be justified or rejected.
*Acceptance:* no-show rate by reminder flag overall and within each visit type; counts shown so
the reader can judge the base rates.

**US-07** As an operations leader, I want to know whether longer waits produce more no-shows so
that access and reliability are treated as one problem.
*Acceptance:* no-show rate by lead-time band with counts.

**US-08** As provider relations, I want realized utilization alongside booked utilization per
provider so that a fully booked provider delivering few visits is not mistaken for a busy one.
*Acceptance:* both measures per provider, plus leakage percent; spread within each specialty
reported.

**US-09** As an operations leader, I want the access recovered from filling cancellations
modeled at several fill rates, in slots, so that I can judge the size of the prize without
being handed an invented dollar figure.
*Acceptance:* three modeled fill rates; output in slots and as a share of completed visits; each
row labelled as modeled opportunity subject to validation.

**US-10** As a patient access manager, I want to see how many waiting patients are already past
their requested-by date so that the backlog's urgency is quantified.
*Acceptance:* count and percent per specialty, with average days waiting.

**US-11** As a business analyst, I want every data-quality failure logged with a severity and
the action taken so that the numbers can be defended.
*Acceptance:* exception log with rule, record, severity, description, action; excluded record
count reconciles to rows in minus rows out.

**US-12** As an analyst, I want to know whether notification opt-in predicts offer acceptance so
that the score component resting on it can be validated.
*Acceptance:* offers made, accepted, and acceptance rate by opt-in status; result reported
whether or not it supports the score.

## Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Lead time derived as appointment date minus request date | Must |
| FR-02 | Access compliance evaluated against a per-specialty standard | Must |
| FR-03 | No-show rate denominator is completed plus no-show, never all appointments | Must |
| FR-04 | Cancellation notice days derived; refillable flag applied at a 3-day threshold | Must |
| FR-05 | Booked and realized utilization calculated separately | Must |
| FR-06 | Waitlist Match Score calculated with five stored component columns | Must |
| FR-07 | Score banded into Low, Moderate, High, Critical | Must |
| FR-08 | Fifteen quality rules executed with severity and action | Must |
| FR-09 | Critical failures excluded from reporting and logged | Must |
| FR-10 | Fill simulation at three rates, expressed in slots only | Must |
| FR-11 | Specialty score component scaled by refillable slots per waiting patient | Should |
| FR-12 | Refillability threshold configurable in one location | Should |
| FR-13 | Reminder and reschedule flags normalized from free-text variants | Must |

## Non-functional requirements

- Full pipeline runs in under 90 seconds on a laptop.
- No patient identifiers; patient grouping only.
- Fixed seed so every number in the docs reproduces.
- No dollar figures anywhere in the outputs.
- Score components stored, not just the total, so any ranking can be explained.

## Traceability

| Story | Requirements | SQL query | Dashboard page | UAT |
|---|---|---|---|---|
| US-01 | FR-01, FR-02 | 3 | Specialty Access Map | UAT-01 |
| US-02 | FR-01, FR-02 | 2 | Patient Access Overview | UAT-02 |
| US-03 | FR-06, FR-07 | 12 | Waitlist Action Queue | UAT-03 |
| US-04 | FR-04 | 7 | Cancellation Opportunity | UAT-04 |
| US-05 | FR-04 | 8 | Cancellation Opportunity | UAT-05 |
| US-06 | FR-03, FR-13 | 4, 5 | No-Show Pattern Analysis | UAT-06 |
| US-07 | FR-01, FR-03 | 6 | No-Show Pattern Analysis | UAT-07 |
| US-08 | FR-05 | 10, 11 | Specialty Access Map | UAT-08 |
| US-09 | FR-10 | 16 | Cancellation Opportunity | UAT-09 |
| US-10 | FR-06 | 14 | Waitlist Action Queue | UAT-10 |
| US-11 | FR-08, FR-09 | 18 | Patient Access Overview | UAT-11 |
| US-12 | FR-06 | 15 | Waitlist Action Queue | UAT-12 |
