-- the aircraft behind the geometric-only uAvionix plots: do they ever send a flight level, and how high are they
WITH per_aircraft AS (
  SELECT common.adshex AS adshex, COUNT(*) AS n,
    COUNTIF(flight_level IS NULL AND geometric_height IS NOT NULL) AS n_geo_only,
    COUNTIF(flight_level IS NOT NULL) AS n_fl,
    COUNTIF(flight_level IS NULL AND geometric_height IS NOT NULL AND target_report_descriptor.is_ground_bit_set) AS n_geo_only_ground,
    APPROX_QUANTILES(IF(flight_level IS NULL, geometric_height, NULL), 10) AS geo_only_height_deciles
  FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
  WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
  GROUP BY adshex HAVING n_geo_only > 0
)
SELECT
  COUNT(*) AS aircraft,
  COUNTIF(n_fl = 0) AS aircraft_never_fl, SUM(IF(n_fl = 0, n_geo_only, 0)) AS plots_from_never_fl,
  COUNTIF(n_fl > 0 AND n_geo_only >= 0.5 * n) AS aircraft_mostly_geo_only, SUM(IF(n_fl > 0 AND n_geo_only >= 0.5 * n, n_geo_only, 0)) AS plots_from_mostly,
  COUNTIF(n_fl > 0 AND n_geo_only < 0.5 * n) AS aircraft_occasional, SUM(IF(n_fl > 0 AND n_geo_only < 0.5 * n, n_geo_only, 0)) AS plots_from_occasional,
  SUM(n_geo_only) AS plots_geo_only, SUM(n_geo_only_ground) AS plots_geo_only_ground,
  APPROX_QUANTILES(geo_only_height_deciles[OFFSET(5)], 100)[OFFSET(50)] AS median_of_aircraft_median_height_ft,
  COUNTIF(geo_only_height_deciles[OFFSET(5)] < 1000) AS aircraft_median_below_1000ft,
  COUNTIF(geo_only_height_deciles[OFFSET(5)] BETWEEN 1000 AND 10000) AS aircraft_median_1k_to_10k,
  COUNTIF(geo_only_height_deciles[OFFSET(5)] > 10000) AS aircraft_median_above_10k
FROM per_aircraft
