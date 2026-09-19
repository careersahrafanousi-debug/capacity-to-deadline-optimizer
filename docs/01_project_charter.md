# Project Charter — Capacity-to-Deadline Optimizer

**Project name:** Capacity-to-Deadline Optimizer
**Organization:** Frontier Specialty Care Network (fictional)
**Prepared by:** Business analyst / data analyst
**Date:** 2026-04-02
**Status:** Prototype, portfolio build

## Problem statement

Patients wait an average of 29.8 days for a specialty appointment and only 59.1% of
appointments meet their specialty's access standard. At the same time roughly one in six booked
slots produces no visit: 8.98% cancel and 8.15% no-show. 507 cancellations in the period
arrived with three or more days notice — enough time to refill — and were not refilled, because
no ranked list exists of which waiting patient to call.

The network has been treating this as a capacity shortage. The data suggests it is primarily a
leakage and matching problem.

## Goal

Measure specialty access against each specialty's own standard, quantify where booked capacity
leaks, and produce a scored, ranked waitlist queue that a scheduler can work when a slot opens.

## Objectives

1. Define and calculate lead time, no-show rate, cancellation rate, and utilization.
2. Separate booked from realized utilization so the leakage gap is visible.
3. Classify cancellations by notice period and identify the refillable population.
4. Score and rank waiting patients with a documented, explainable formula.
5. Model the access recovered at three fill rates, in slots rather than dollars.
6. Enforce fifteen data-quality rules so the metrics are defensible.

## Users

| User | Primary use |
|---|---|
| Patient access manager | Lead time by specialty and visit type against standard |
| Scheduling supervisors | The ranked action queue |
| Specialty clinic leads | Their own access position and leakage |
| Provider relations | Realized utilization spread among peers |
| Operations leadership | Whether to add capacity or fix leakage |
| Business analyst | Definitions, rules, traceability, UAT |

## Success measures

| Measure | Baseline (modeled) | Target direction |
|---|---|---|
| Average lead time | 29.8 days | Decrease |
| Within access standard | 59.1% | Increase |
| New-patient within standard | 31.4% | Increase, reported separately |
| No-show rate | 8.15% | Decrease |
| Reminder coverage | 7,403 of 10,234 attended-or-missed appointments | Approach 100% |
| Refillable cancellations filled | Not currently tracked | Establish, then increase |
| Waitlist patients past requested-by date | 53.0% | Decrease |
| Realized utilization spread within a specialty | Up to 20.6 points | Narrow |

## Scope

**In scope:** 13,951 appointments and 1,786 waitlist entries, six specialties, 22 providers,
requests dated 2026-01-05 to 2026-06-26; metric definitions, quality rules, waitlist scoring,
fill simulation, dashboard specification.

**Out of scope:** staffing and session planning, referral source analysis, clinical
appropriateness of visit type, payer mix and reimbursement, patient-level identity, transport
provision.

## Assumptions

- A cancellation with three or more days notice is refillable. Judgement call, configurable in
  one place in `src/clean_and_score.py`.
- Each specialty is judged against its own access standard (14, 21, or 30 days).
- Waitlist score weights are analyst judgement, not fitted to outcomes.
- Recovered slots complete at the same rate as ordinary bookings. Optimistic, stated as such.
- No production data is used.

## Constraints

- No patient identifiers of any kind; patients appear only as Group A-D.
- Must run without a server database.
- The score must be explainable to a scheduler in one sentence per component, or it will not be
  trusted or used.

## Risks

| Risk | Mitigation |
|---|---|
| Score treated as a clinical priority tool | Score is explicitly an operational matching aid; clinical urgency is out of scope and documented as such |
| Unfitted weights presented as validated | Limitations state the weights are judgement; finding 8 shows one component already contradicted by evidence |
| Fill simulation quoted as revenue | Output is slots and share of completed visits only; no dollar figure appears anywhere in the repo |
| Blended access metrics hide new-patient failure | New patient reported separately as a standing requirement |
| Refillability threshold set to flatter the result | Threshold stated, single point of change, sensitivity is the obvious next test |

## Deliverables

Charter, business requirements, data dictionary, synthetic data generator, cleaning and scoring
pipeline, fifteen documented quality rules, exception log, SQL analysis set, fill simulation,
as-is and to-be process maps, dashboard specification, UAT test cases, executive summary.
