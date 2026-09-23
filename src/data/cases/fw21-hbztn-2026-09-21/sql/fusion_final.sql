
SELECT t.* FROM `flyways.uni_track_provider.fused_plots_aws` t JOIN UNNEST([
    STRUCT('fw21-hbztn-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 06:30:38') AS t0, TIMESTAMP('2026-09-21 07:30:38') AS t1, 46.405 AS lat_min, 48.092 AS lat_max, 6.93 AS lon_min, 8.079 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 06:30:38') AND t.position_timestamp < TIMESTAMP('2026-09-21 07:30:38') AND t.latitude BETWEEN 46.405 AND 48.092 AND t.longitude BETWEEN 6.93 AND 8.079))

