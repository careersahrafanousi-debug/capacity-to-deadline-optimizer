-- Capacity-to-Deadline Optimizer - patient access analysis
-- Frontier Specialty Care Network (fictional org, fully synthetic data)
-- SQLite dialect. Postgres: replace julianday() with date subtraction.

--------------------------------------------------------------------
-- 1. Access summary - the four headline metrics
--------------------------------------------------------------------
SELECT COUNT(*)                                                          AS appointments,
       ROUND(AVG(Lead_Time_Days), 1)                                     AS avg_lead_time_days,
       ROUND(100.0 * SUM(CASE WHEN Status = 'No Show' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN Status IN ('Completed', 'No Show')
                               THEN 1 ELSE 0 END), 0), 2)                AS no_show_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN Status = 'Cancelled' THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                              AS cancellation_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN Lead_Time_Within_Standard = 'Yes' THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                              AS within_access_standard_pct
FROM appointments;


--------------------------------------------------------------------
-- 2. Lead time by visit type - new patients wait longest
--------------------------------------------------------------------
SELECT Visit_Type,
       COUNT(*)                          AS appointments,
       ROUND(AVG(Lead_Time_Days), 1)     AS avg_lead_time_days,
       MIN(Lead_Time_Days)               AS min_days,
       MAX(Lead_Time_Days)               AS max_days,
       ROUND(100.0 * SUM(CASE WHEN Lead_Time_Within_Standard = 'Yes' THEN 1 ELSE 0 END)
             / COUNT(*), 1)              AS within_standard_pct
FROM appointments
GROUP BY Visit_Type
ORDER BY avg_lead_time_days DESC;


--------------------------------------------------------------------
-- 3. Access map by specialty against its own standard
--------------------------------------------------------------------
SELECT a.Specialty,
       s.Target_Lead_Time_Days,
       s.Access_Standard,
       COUNT(*)                                      AS appointments,
       ROUND(AVG(a.Lead_Time_Days), 1)               AS avg_lead_time_days,
       ROUND(100.0 * SUM(CASE WHEN a.Lead_Time_Within_Standard = 'Yes'
                              THEN 1 ELSE 0 END) / COUNT(*), 1) AS within_standard_pct
FROM appointments a
JOIN dim_specialty s ON s.Specialty = a.Specialty
GROUP BY a.Specialty, s.Target_Lead_Time_Days, s.Access_Standard
ORDER BY within_standard_pct;


--------------------------------------------------------------------
-- 4. Does the reminder actually change the no-show rate?
--------------------------------------------------------------------
SELECT Reminder_Sent,
       COUNT(*)                                                    AS attended_or_missed,
       SUM(CASE WHEN Status = 'No Show' THEN 1 ELSE 0 END)          AS no_shows,
       ROUND(100.0 * SUM(CASE WHEN Status = 'No Show' THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                        AS no_show_rate_pct
FROM appointments
WHERE Status IN ('Completed', 'No Show')
GROUP BY Reminder_Sent
ORDER BY no_show_rate_pct DESC;


--------------------------------------------------------------------
-- 5. No-show rate by visit type and reminder together
-- Checks whether the reminder effect holds inside each visit type
-- rather than being an artifact of who gets reminders.
--------------------------------------------------------------------
SELECT Visit_Type,
       Reminder_Sent,
       COUNT(*)                                                   AS n,
       ROUND(100.0 * SUM(CASE WHEN Status = 'No Show' THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                       AS no_show_rate_pct
FROM appointments
WHERE Status IN ('Completed', 'No Show')
GROUP BY Visit_Type, Reminder_Sent
ORDER BY Visit_Type, Reminder_Sent;


--------------------------------------------------------------------
-- 6. Do long waits erode show rates?
--------------------------------------------------------------------
SELECT CASE WHEN Lead_Time_Days <= 14 THEN '1. 0-14 days'
            WHEN Lead_Time_Days <= 30 THEN '2. 15-30 days'
            WHEN Lead_Time_Days <= 60 THEN '3. 31-60 days'
            ELSE '4. 60+ days' END                                AS lead_time_band,
       COUNT(*)                                                   AS n,
       ROUND(100.0 * SUM(CASE WHEN Status = 'No Show' THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                       AS no_show_rate_pct
FROM appointments
WHERE Status IN ('Completed', 'No Show')
GROUP BY lead_time_band
ORDER BY lead_time_band;


--------------------------------------------------------------------
-- 7. Cancellation opportunity - how much notice do we get?
--------------------------------------------------------------------
SELECT CASE WHEN Cancel_Notice_Days IS NULL THEN '0. No cancellation date recorded'
            WHEN Cancel_Notice_Days = 0 THEN '1. Same day'
            WHEN Cancel_Notice_Days <= 2 THEN '2. 1-2 days notice'
            WHEN Cancel_Notice_Days <= 7 THEN '3. 3-7 days notice'
            ELSE '4. Over 7 days notice' END                       AS notice_band,
       COUNT(*)                                                    AS cancellations,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM appointments
                                 WHERE Status = 'Cancelled'), 1)   AS pct_of_cancellations
FROM appointments
WHERE Status = 'Cancelled'
GROUP BY notice_band
ORDER BY notice_band;


--------------------------------------------------------------------
-- 8. Refillable cancellations by specialty and time block
-- This is the supply side of the waitlist match.
--------------------------------------------------------------------
SELECT Specialty,
       Time_Block,
       COUNT(*)                                                    AS refillable_slots,
       ROUND(AVG(Cancel_Notice_Days), 1)                           AS avg_notice_days
FROM appointments
WHERE Status = 'Cancelled' AND Refillable = 'Yes'
GROUP BY Specialty, Time_Block
ORDER BY refillable_slots DESC;


--------------------------------------------------------------------
-- 9. Cancellation reasons - which are addressable?
--------------------------------------------------------------------
SELECT Cancellation_Reason,
       COUNT(*)                                                    AS cancellations,
       SUM(CASE WHEN Refillable = 'Yes' THEN 1 ELSE 0 END)         AS refillable,
       ROUND(AVG(Cancel_Notice_Days), 1)                           AS avg_notice_days
FROM appointments
WHERE Status = 'Cancelled'
GROUP BY Cancellation_Reason
ORDER BY cancellations DESC;


--------------------------------------------------------------------
-- 10. Provider utilization - the spread inside a single specialty
--------------------------------------------------------------------
SELECT c.Specialty,
       c.Provider_ID,
       SUM(c.Available_Slots)                                      AS available_slots,
       SUM(c.Booked_Slots)                                         AS booked_slots,
       SUM(c.Completed_Slots)                                      AS completed_slots,
       ROUND(100.0 * SUM(c.Booked_Slots) / NULLIF(SUM(c.Available_Slots), 0), 1)
                                                                   AS booked_utilization_pct,
       ROUND(100.0 * SUM(c.Completed_Slots) / NULLIF(SUM(c.Available_Slots), 0), 1)
                                                                   AS realized_utilization_pct,
       ROUND(100.0 * (SUM(c.Cancelled_Slots) + SUM(c.No_Show_Slots))
             / NULLIF(SUM(c.Booked_Slots), 0), 1)                  AS leakage_pct
FROM provider_capacity c
GROUP BY c.Specialty, c.Provider_ID
ORDER BY c.Specialty, realized_utilization_pct;


--------------------------------------------------------------------
-- 11. Utilization spread by specialty - min to max within the group
--------------------------------------------------------------------
WITH prov AS (
    SELECT Specialty, Provider_ID,
           100.0 * SUM(Completed_Slots) / NULLIF(SUM(Available_Slots), 0) AS util
    FROM provider_capacity
    GROUP BY Specialty, Provider_ID
)
SELECT Specialty,
       COUNT(*)                     AS providers,
       ROUND(MIN(util), 1)          AS lowest_utilization_pct,
       ROUND(MAX(util), 1)          AS highest_utilization_pct,
       ROUND(MAX(util) - MIN(util), 1) AS spread_pp
FROM prov
GROUP BY Specialty
ORDER BY spread_pp DESC;


--------------------------------------------------------------------
-- 12. Waitlist action queue - who to call first
--------------------------------------------------------------------
SELECT Waitlist_ID, Specialty, Match_Priority, Waitlist_Match_Score,
       Days_Waiting, Days_To_Requested_By, Preferred_Time,
       Travel_Category, Notification_Opt_In,
       Score_Specialty, Score_Urgency, Score_Time_Match,
       Score_Notification, Score_Reschedule_Ready
FROM waitlist
ORDER BY Waitlist_Match_Score DESC, Days_Waiting DESC
LIMIT 50;


--------------------------------------------------------------------
-- 13. Waitlist priority distribution, with supply context
--------------------------------------------------------------------
SELECT Specialty,
       COUNT(*)                                                     AS waiting_patients,
       MAX(Spec_Open_Slots)                                         AS refillable_slots,
       ROUND(MAX(Slots_Per_Waiting_Patient), 3)                     AS slots_per_patient,
       SUM(CASE WHEN Match_Priority = 'Critical' THEN 1 ELSE 0 END)  AS critical,
       SUM(CASE WHEN Match_Priority = 'High' THEN 1 ELSE 0 END)      AS high,
       SUM(CASE WHEN Match_Priority = 'Moderate' THEN 1 ELSE 0 END)  AS moderate,
       SUM(CASE WHEN Match_Priority = 'Low' THEN 1 ELSE 0 END)       AS low,
       ROUND(AVG(Waitlist_Match_Score), 1)                           AS avg_score
FROM waitlist
GROUP BY Specialty
ORDER BY avg_score DESC;


--------------------------------------------------------------------
-- 14. Waitlist patients already past their requested-by date
--------------------------------------------------------------------
SELECT Specialty,
       COUNT(*)                                                      AS total_waiting,
       SUM(CASE WHEN Days_To_Requested_By < 0 THEN 1 ELSE 0 END)      AS past_requested_by,
       ROUND(100.0 * SUM(CASE WHEN Days_To_Requested_By < 0 THEN 1 ELSE 0 END)
             / COUNT(*), 1)                                          AS pct_past_requested_by,
       ROUND(AVG(Days_Waiting), 1)                                    AS avg_days_waiting
FROM waitlist
GROUP BY Specialty
ORDER BY pct_past_requested_by DESC;


--------------------------------------------------------------------
-- 15. Offer outcomes - does opt-in predict acceptance?
--------------------------------------------------------------------
SELECT Notification_Opt_In,
       COUNT(*)                                                       AS waitlist_entries,
       SUM(CASE WHEN Offered_Slot_Date IS NOT NULL THEN 1 ELSE 0 END)  AS offers_made,
       SUM(CASE WHEN Offer_Accepted = 'Yes' THEN 1 ELSE 0 END)         AS offers_accepted,
       ROUND(100.0 * SUM(CASE WHEN Offer_Accepted = 'Yes' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN Offered_Slot_Date IS NOT NULL THEN 1 ELSE 0 END), 0), 1)
                                                                      AS acceptance_rate_pct
FROM waitlist
GROUP BY Notification_Opt_In
ORDER BY acceptance_rate_pct DESC;


--------------------------------------------------------------------
-- 16. Fill simulation results
--------------------------------------------------------------------
SELECT * FROM fill_simulation;


--------------------------------------------------------------------
-- 17. Monthly access trend
--------------------------------------------------------------------
SELECT strftime('%Y-%m', Request_Date)                               AS request_month,
       COUNT(*)                                                      AS requests,
       ROUND(AVG(Lead_Time_Days), 1)                                 AS avg_lead_time_days,
       ROUND(100.0 * SUM(CASE WHEN Status = 'Cancelled' THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                          AS cancellation_rate_pct
FROM appointments
GROUP BY request_month
ORDER BY request_month;


--------------------------------------------------------------------
-- 18. Data quality exceptions by rule
--------------------------------------------------------------------
SELECT Rule_ID, Severity, Action_Taken, COUNT(*) AS exceptions
FROM dq_exceptions
GROUP BY Rule_ID, Severity, Action_Taken
ORDER BY exceptions DESC;
