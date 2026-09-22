-- uAvionix, one day: how often a barometric-first mapping would have to fall back to geometric height
SELECT
  COUNT(*) AS n,
  COUNTIF(flight_level IS NOT NULL) AS n_fl,
  COUNTIF(flight_level IS NULL AND geometric_height IS NOT NULL) AS n_geo_only,
  COUNTIF(flight_level IS NULL AND geometric_height IS NOT NULL AND target_report_descriptor.is_ground_bit_set) AS n_geo_only_ground_bit,
  COUNTIF(flight_level IS NULL AND geometric_height IS NULL) AS n_neither,
  COUNTIF(flight_level IS NULL AND geometric_height IS NULL AND target_report_descriptor.is_ground_bit_set) AS n_neither_ground_bit,
  APPROX_QUANTILES(IF(flight_level IS NULL, geometric_height, NULL), 100)[OFFSET(50)] AS geo_only_height_p50,
  APPROX_QUANTILES(IF(flight_level IS NULL, geometric_height, NULL), 100)[OFFSET(90)] AS geo_only_height_p90,
  COUNT(DISTINCT IF(flight_level IS NULL AND geometric_height IS NOT NULL, target_address, NULL)) AS geo_only_aircraft,
  COUNT(DISTINCT target_address) AS aircraft
FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
