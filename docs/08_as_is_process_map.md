# As-Is Scheduling Process — Frontier Specialty Care Network

```mermaid
flowchart TD
    A[Referral or patient call] --> B[Scheduler searches for the next open slot]
    B --> C{Slot available inside the access standard?}
    C -->|Yes| D[Book appointment]
    C -->|No| E[Book the first slot available, often weeks out]:::pain
    E --> F[Patient optionally added to the waitlist]:::pain
    F --> G[Waitlist held as a flat list, no ranking]:::pain
    D --> H[Reminder sent, if someone remembers]:::pain
    E --> H
    H --> I{Patient attends?}
    I -->|Yes| J[Visit completed]
    I -->|No show| K[Slot lost, no follow-up]:::pain
    I -->|Cancels| L[Cancellation logged, date often blank]:::pain
    L --> M{Anyone available to refill?}
    M -->|No time| N[Slot goes unused]:::pain
    M -->|Maybe| O[Scheduler calls whoever they remember]:::pain
    G --> P[Patient waits past their requested-by date]:::pain
    P --> Q[Patient disengages or presents elsewhere]:::pain
    N --> R[Access metrics worsen, pressure to add capacity]:::pain

    classDef pain fill:#ffe0e0,stroke:#cc0000,color:#000
```

## Where it breaks

| # | Breakdown | Evidence in the data |
|---|---|---|
| 1 | Long waits accepted as normal | Average lead time 29.8 days; only 59.1% within standard |
| 2 | New patients absorb the failure | 44.2 days average, 31.4% within standard |
| 3 | Reminders sent inconsistently | 2,831 attended-or-missed appointments had no reminder |
| 4 | No-shows not followed up | 834 no-shows; no rebooking or pattern tracking |
| 5 | Cancellation date not captured | 60 cancelled appointments cannot be assessed for refill |
| 6 | Refillable slots not refilled | 507 cancellations arrived with 3+ days notice |
| 7 | Waitlist unranked | 1,786 waiting patients held as a flat list |
| 8 | Waitlist urgency invisible | 946 patients (53.0%) already past their requested-by date |
| 9 | Utilization judged on bookings, not visits | PRV-019 booked 72%, realizes 50.6% |
| 10 | Capacity treated as the only lever | Realized utilization spread of 20.6 points inside pulmonology |

## Consequence

Roughly one in six booked slots produces no visit. The network is under pressure to add
sessions while 507 already-paid-for slots went unfilled in six months, and the longer patients
wait, the less likely they are to arrive — no-show rates climb from 6.32% under two weeks to
13.79% beyond sixty days. The loop reinforces itself.
