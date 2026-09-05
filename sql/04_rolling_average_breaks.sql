-- Days that beat their own trailing 7-day average by more than two standard
-- deviations of that same window. These are the days a naive forecast misses.
WITH windowed AS (
    SELECT
        date, day_name, energy_met_mu,
        AVG(energy_met_mu) OVER (ORDER BY date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS roll_avg,
        is_holiday, holiday_name
    FROM daily
    WHERE energy_met_mu IS NOT NULL
),
spread AS (SELECT AVG(ABS(energy_met_mu - roll_avg)) * 1.2533 AS sd_est
           FROM windowed WHERE roll_avg IS NOT NULL)
SELECT
    w.date, w.day_name,
    ROUND(w.energy_met_mu, 1) AS demand_mu,
    ROUND(w.roll_avg, 1)      AS trailing_7day_mu,
    ROUND(w.energy_met_mu - w.roll_avg, 1) AS gap_mu,
    CASE WHEN w.is_holiday = 1 THEN w.holiday_name ELSE '' END AS holiday
FROM windowed w CROSS JOIN spread s
WHERE w.roll_avg IS NOT NULL
  AND ABS(w.energy_met_mu - w.roll_avg) > 2 * s.sd_est
ORDER BY ABS(w.energy_met_mu - w.roll_avg) DESC
LIMIT 20;
