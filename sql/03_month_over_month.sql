-- Month on month percentage change in average daily demand.
-- LAG reaches back one row in the ordered monthly series.
WITH monthly AS (
    SELECT strftime('%Y-%m', date) AS ym,
           AVG(energy_met_mu)      AS avg_mu,
           COUNT(*)                AS days
    FROM daily
    WHERE energy_met_mu IS NOT NULL
    GROUP BY ym
    HAVING days >= 25          -- ignore months the source only half covers
)
SELECT
    ym,
    days,
    ROUND(avg_mu, 1) AS avg_mu,
    ROUND(LAG(avg_mu) OVER (ORDER BY ym), 1) AS prev_month_mu,
    ROUND(100.0 * (avg_mu / LAG(avg_mu) OVER (ORDER BY ym) - 1), 2) AS mom_pct
FROM monthly
ORDER BY ym;
