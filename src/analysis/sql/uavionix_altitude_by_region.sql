-- uAvionix altitude kinds by 1-degree cell, one day. Which fields are present, what altitude_ft equals, and the gap.
SELECT
  CAST(FLOOR(common.latitude) AS INT64) AS lat_cell, CAST(FLOOR(common.longitude) AS INT64) AS lon_cell,
  COUNT(*) AS n,
  COUNTIF(geometric_height IS NOT NULL) AS n_geo,
  COUNTIF(flight_level IS NOT NULL) AS n_fl,
  COUNTIF(common.altitude_ft IS NULL) AS n_alt_null,
  COUNTIF(common.altitude_ft = CAST(geometric_height AS INT64)) AS n_alt_is_geo,
  COUNTIF(geometric_height IS NULL AND common.altitude_ft = CAST(flight_level * 100 AS INT64)) AS n_alt_is_fl,
  COUNTIF(target_report_descriptor.is_ground_bit_set) AS n_ground_bit,
  APPROX_QUANTILES(geometric_height - flight_level * 100, 100)[OFFSET(50)] AS gap_p50,
  APPROX_QUANTILES(geometric_height - flight_level * 100, 100)[OFFSET(10)] AS gap_p10,
  APPROX_QUANTILES(geometric_height - flight_level * 100, 100)[OFFSET(90)] AS gap_p90,
  APPROX_QUANTILES(flight_level * 100, 100)[OFFSET(50)] AS fl_ft_p50
FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
GROUP BY lat_cell, lon_cell
HAVING n >= 1000
ORDER BY n DESC
