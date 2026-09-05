-- Karnataka's share of all-India energy met, by year.
-- states_daily is the long table: one row per state per day.
WITH by_year AS (
    SELECT CAST(strftime('%Y', date) AS INT) AS yr,
           SUM(CASE WHEN state = 'Karnataka' THEN energy_met_mu ELSE 0 END) AS ka_mu,
           SUM(energy_met_mu) AS india_mu,
           COUNT(DISTINCT date) AS days
    FROM state_daily
    GROUP BY yr
    HAVING days >= 300
)
SELECT yr, days,
       ROUND(ka_mu / 1000.0, 1)    AS ka_bu,
       ROUND(india_mu / 1000.0, 1) AS india_bu,
       ROUND(100.0 * ka_mu / india_mu, 2) AS ka_share_pct
FROM by_year
ORDER BY yr;
