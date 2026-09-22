-- STDDS one day: is the altitude present, which kind does the report say it is, and is the raw barometric altitude there too
SELECT
  COUNT(*) AS n,
  COUNTIF(position.altitude IS NOT NULL) AS n_alt,
  COUNTIF(status.uncorr_baro_alt IS NOT NULL) AS n_uncorr_baro,
  COUNTIF(status.mrh = 1) AS n_mrh_barometric, COUNTIF(status.mrh = 2) AS n_mrh_geometric, COUNTIF(status.mrh = 0 OR status.mrh IS NULL) AS n_mrh_unset,
  APPROX_QUANTILES(position.altitude - status.uncorr_baro_alt * 100, 100)[OFFSET(50)] AS alt_minus_baro_p50,
  APPROX_QUANTILES(position.altitude - status.uncorr_baro_alt * 100, 100)[OFFSET(10)] AS alt_minus_baro_p10,
  APPROX_QUANTILES(position.altitude - status.uncorr_baro_alt * 100, 100)[OFFSET(90)] AS alt_minus_baro_p90
FROM `flyways-aws-prod.uni_track_source_stdds.uni_track_source_stdds_position_reports`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
