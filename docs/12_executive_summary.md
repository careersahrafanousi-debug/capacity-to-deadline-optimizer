# Executive Summary — Capacity-to-Deadline Optimizer

**Organization:** Frontier Specialty Care Network (fictional)
**Period analyzed:** 2026-01-05 to 2026-06-26
**Population:** 13,951 appointments, 1,786 waitlist entries, 22 providers, 6 specialties
**Data:** Fully synthetic

## The headline

The network is being asked to add capacity. The data says the first problem is leakage.

Patients wait **29.8 days on average** and only **59.1%** of appointments meet their specialty's
access standard. Meanwhile roughly one in six booked slots produces no visit — **8.98% cancel,
8.15% no-show** — and **507 cancellations arrived with three or more days notice** and were not
refilled. There is no ranked list of who to call, so nobody calls.

## Five findings that matter

**1. Reminders more than halve no-shows, and 2,831 appointments did not get one.**
5.27% no-show with a reminder against 15.68% without. The effect holds inside every visit type
(new patients 7.11% vs 22.96%), so it is not an artifact of who receives reminders. This is the
largest and cheapest movement available and it requires no analytics to act on.

**2. New patients absorb almost all of the access failure.**
44.2 days average lead time and only 31.4% within standard, against 23.1 days and 73.2% for
established patients. Any blended access figure hides a 21-day gap. New-patient access needs its
own line on every report.

**3. Waiting longer makes patients less likely to arrive.**
No-show rate climbs from 6.32% under two weeks to 13.79% beyond sixty days. Access and
reliability are one problem, and the queue feeds itself.

**4. Over half the waitlist is already late.**
946 of 1,786 waiting patients (53.0%) are past the date they asked to be seen by, averaging 44.1
days waiting. Endocrinology is worst at 58.0%.

**5. Providers in the same specialty deliver very different volumes.**
Realized utilization ranges 50.6% to 71.2% across four pulmonologists — a 20.6 point spread — and
57.4% to 75.4% in orthopedics. Booked utilization conceals this entirely: one provider is booked
at 72% and realizes 50.6%, another is booked to 100% and realizes 71.2%.

A useful negative finding sits alongside these: once each specialty is judged against its own
standard, compliance is uniform at 57-61%. There is no single failing clinic. This is a
network-wide process problem.

## What was built

A scored waitlist queue. Each waiting patient carries a **Waitlist Match Score** out of 100
built from five stated components — specialty supply match (35), lead-time urgency (25), time
preference match (20), notification opt-in (10), reschedule readiness (10) — banded into Low,
Moderate, High, and Critical. The current queue holds **316 Critical** and **704 High** priority
patients, ranked, with every component visible so a scheduler can see why a patient is first.

The specialty component scales by refillable slots per waiting patient rather than awarding a
flat 35 for a matching specialty, because a flat award would rank nothing.

## Modeled opportunity

| Modeled fill rate | Slots recovered | Share of completed visits |
|---|---|---|
| 30% | 152 | 1.62% |
| 50% | 254 | 2.70% |
| 70% | 355 | 3.78% |

Reported in slots only. No revenue or savings figure appears anywhere in this project — any such
number would be invented. These are modeled opportunities subject to validation with scheduling
staff, and the 507 refillable slots they rest on is a floor, because 60 cancellations have no
recorded date and cannot be assessed at all.

## Recommendations

1. **Automatic reminders on every appointment.** Closes a 2,831-appointment gap with the largest
   measured effect in the dataset.
2. **Make the cancellation date mandatory.** A form field, not a project. Recovers 60
   unassessable records per six months.
3. **Publish the waitlist action queue** and let schedulers work it top down.
4. **Report new-patient access separately** against its own target.
5. **Review realized — not booked — utilization with provider relations** before adding
   sessions.
6. **Capture offer outcomes and review the score weights monthly.**

## Honest caveats

The weights in the Match Score are analyst judgement, not fitted to outcomes, and the data
already contradicts one of them: notification opt-in patients accept offers at 54.0% against
55.9% for non-opt-in. That component was justified on speed of contact rather than intent, but
it has not been validated and is logged as defect D-01.

Access compliance is measured against each specialty's target lead time, not its published
access standard, and those differ — orthopedics targets 19 days against a published 14. Measured
against the published standard, compliance would be materially worse. That definitional question
needs settling with the access manager before any of these figures are published externally.

All data is synthetic, the patterns were generated rather than observed, and nothing here
establishes causation.
