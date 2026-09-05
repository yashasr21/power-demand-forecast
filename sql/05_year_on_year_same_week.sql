-- Same calendar week, this year against last year. Week 53 is dropped because
-- it is a stub week in most years and the comparison is meaningless.
WITH weekly AS (
    SELECT CAST(strftime('%Y', date) AS INT) AS yr,
           CAST(strftime('%W', date) AS INT) AS wk,
           AVG(energy_met_mu) AS avg_mu,
           COUNT(*)           AS days
    FROM daily
    WHERE energy_met_mu IS NOT NULL
    GROUP BY yr, wk
    HAVING days = 7
)
SELECT
    yr, wk,
    ROUND(avg_mu, 1) AS avg_mu,
    ROUND(LAG(avg_mu) OVER (PARTITION BY wk ORDER BY yr), 1) AS same_week_last_year,
    ROUND(100.0 * (avg_mu / LAG(avg_mu) OVER (PARTITION BY wk ORDER BY yr) - 1), 2) AS yoy_pct
FROM weekly
WHERE wk < 53
ORDER BY yr, wk;
