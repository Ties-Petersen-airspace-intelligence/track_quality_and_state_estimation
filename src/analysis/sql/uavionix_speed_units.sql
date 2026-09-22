-- uAvionix one day: the ground speed in the common header, by height band. Knots would be hundreds at cruise.
SELECT
  CASE WHEN common.altitude_ft IS NULL THEN 'no altitude' WHEN common.altitude_ft = 0 THEN 'altitude 0' WHEN common.altitude_ft < 10000 THEN 'below 10k' ELSE 'above 10k' END AS band,
  COUNT(*) AS n,
  COUNTIF(common.ground_speed_kt IS NOT NULL) AS n_speed,
  APPROX_QUANTILES(common.ground_speed_kt, 100)[OFFSET(50)] AS speed_p50,
  APPROX_QUANTILES(common.ground_speed_kt, 100)[OFFSET(90)] AS speed_p90,
  MAX(common.ground_speed_kt) AS speed_max,
  COUNTIF(common.ground_speed_kt > 5) AS n_speed_over_5,
  APPROX_QUANTILES(airborne_ground_vector.ground_speed, 100)[OFFSET(50)] AS raw_vector_speed_p50
FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
GROUP BY band ORDER BY band
