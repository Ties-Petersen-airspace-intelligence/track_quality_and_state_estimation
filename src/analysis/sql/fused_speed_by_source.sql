-- production fused plots one day: ground speed per source, so we can see what uAvionix rows carry downstream
SELECT source_identifier, COUNT(*) AS n, COUNTIF(ground_speed_kt IS NOT NULL) AS n_speed,
  APPROX_QUANTILES(ground_speed_kt, 100)[OFFSET(50)] AS speed_p50, APPROX_QUANTILES(ground_speed_kt, 100)[OFFSET(90)] AS speed_p90,
  COUNTIF(ground_speed_kt < 1) AS n_speed_under_1, COUNTIF(altitude_ft > 5000 AND ground_speed_kt < 1) AS n_airborne_under_1
FROM `flyways.uni_track_provider.fused_plots_aws`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
GROUP BY source_identifier ORDER BY n DESC
