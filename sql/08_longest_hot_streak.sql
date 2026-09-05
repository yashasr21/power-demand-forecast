-- Longest unbroken run of days above the all-time average.
-- The trick is the gaps-and-islands one: subtract a row number from a running
-- counter and consecutive days end up sharing a group id.
WITH flagged AS (
    SELECT date, energy_met_mu,
           CASE WHEN energy_met_mu > (SELECT AVG(energy_met_mu) FROM daily
                                      WHERE energy_met_mu IS NOT NULL)
                THEN 1 ELSE 0 END AS above
    FROM daily
    WHERE energy_met_mu IS NOT NULL
),
grouped AS (
    SELECT date, energy_met_mu, above,
           ROW_NUMBER() OVER (ORDER BY date)
         - ROW_NUMBER() OVER (PARTITION BY above ORDER BY date) AS island
    FROM flagged
)
SELECT MIN(date) AS run_start, MAX(date) AS run_end, COUNT(*) AS days,
       ROUND(AVG(energy_met_mu), 1) AS avg_mu, ROUND(MAX(energy_met_mu), 1) AS peak_mu
FROM grouped
WHERE above = 1
GROUP BY island
ORDER BY days DESC
LIMIT 10;
