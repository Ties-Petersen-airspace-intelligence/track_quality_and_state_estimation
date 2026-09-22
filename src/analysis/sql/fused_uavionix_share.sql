-- how many production fused plots came from each source on one day, and how far uAvionix altitude sits from its own flight level (not available here), so just the share
SELECT source_identifier, COUNT(*) AS n, COUNTIF(valid_to IS NULL) AS n_current,
  APPROX_QUANTILES(altitude_ft, 100)[OFFSET(50)] AS alt_p50
FROM `flyways.uni_track_provider.fused_plots_aws`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
GROUP BY source_identifier ORDER BY n DESC
