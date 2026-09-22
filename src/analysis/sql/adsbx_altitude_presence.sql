-- ADS-B Exchange, one day, all coverage: how often barometric and geometric altitude are present, by region
SELECT
  CASE WHEN common.latitude BETWEEN 15 AND 75 AND common.longitude BETWEEN -170 AND -50 THEN 'North America'
       WHEN common.latitude BETWEEN 35 AND 72 AND common.longitude BETWEEN -25 AND 45 THEN 'Europe'
       WHEN common.latitude BETWEEN 10 AND 45 AND common.longitude BETWEEN 25 AND 65 THEN 'Middle East'
       WHEN common.latitude BETWEEN -10 AND 55 AND common.longitude BETWEEN 65 AND 150 THEN 'Asia'
       WHEN common.latitude BETWEEN -50 AND 15 AND common.longitude BETWEEN -90 AND -30 THEN 'South America'
       WHEN common.latitude BETWEEN -50 AND -10 AND common.longitude BETWEEN 110 AND 180 THEN 'Oceania'
       ELSE 'other' END AS region,
  COUNT(*) AS n,
  COUNTIF(alt_baro IS NOT NULL AND alt_baro != '-1') AS n_baro,
  COUNTIF(alt_baro = 'ground') AS n_ground,
  COUNTIF(alt_geom IS NOT NULL) AS n_geo,
  COUNTIF(alt_baro IS NOT NULL AND alt_baro != '-1' AND alt_geom IS NOT NULL) AS n_both
FROM `uni-adsbx-integration-master.adsbx_integration.adsbx_positions`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
GROUP BY region ORDER BY n DESC
