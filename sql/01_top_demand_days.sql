-- The ten heaviest days on record, with the weather on that day.
-- temp_max_c is NULL until src/03_get_weather.py has been run.
SELECT
    date,
    day_name,
    ROUND(energy_met_mu, 1) AS demand_mu,
    temp_max_c,
    CASE WHEN is_holiday = 1 THEN holiday_name ELSE '' END AS holiday
FROM daily
WHERE energy_met_mu IS NOT NULL
ORDER BY energy_met_mu DESC
LIMIT 10;
