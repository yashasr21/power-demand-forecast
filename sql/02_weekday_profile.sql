-- Average demand by day of week, and how far each day sits from the overall
-- average. Cross join gives every row the same grand mean to compare against.
SELECT
    d.day_name,
    COUNT(*)                                        AS days,
    ROUND(AVG(d.energy_met_mu), 1)                  AS avg_mu,
    ROUND(AVG(d.energy_met_mu) - g.grand_mean, 1)   AS diff_from_all_days_mu,
    ROUND(100.0 * (AVG(d.energy_met_mu) / g.grand_mean - 1), 2) AS diff_pct
FROM daily d
CROSS JOIN (SELECT AVG(energy_met_mu) AS grand_mean
            FROM daily WHERE energy_met_mu IS NOT NULL) g
WHERE d.energy_met_mu IS NOT NULL
GROUP BY d.day_name, g.grand_mean
ORDER BY avg_mu DESC;
