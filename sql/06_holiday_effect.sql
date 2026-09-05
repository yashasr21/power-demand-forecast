-- How much quieter is a holiday than the same weekday around it?
-- The comparison is against the same day of week in the same month and year,
-- so a Sunday holiday is not scored against a Tuesday.
WITH normal AS (
    SELECT strftime('%Y-%m', date) AS ym, day_name,
           AVG(energy_met_mu) AS normal_mu, COUNT(*) AS n
    FROM daily
    WHERE energy_met_mu IS NOT NULL AND is_holiday = 0
    GROUP BY ym, day_name
    HAVING n >= 2
)
SELECT
    h.holiday_name,
    COUNT(*) AS occurrences,
    ROUND(AVG(h.energy_met_mu), 1) AS avg_holiday_mu,
    ROUND(AVG(n.normal_mu), 1)     AS avg_normal_mu,
    ROUND(100.0 * (AVG(h.energy_met_mu) / AVG(n.normal_mu) - 1), 2) AS diff_pct
FROM daily h
JOIN normal n
  ON n.ym = strftime('%Y-%m', h.date) AND n.day_name = h.day_name
WHERE h.is_holiday = 1 AND h.energy_met_mu IS NOT NULL
GROUP BY h.holiday_name
HAVING occurrences >= 5
ORDER BY diff_pct;
