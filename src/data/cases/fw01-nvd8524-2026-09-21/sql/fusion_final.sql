
SELECT t.* FROM `flyways.uni_track_provider.fused_plots_aws` t JOIN UNNEST([
    STRUCT('fw01-nvd8524-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 09:30:10') AS t0, TIMESTAMP('2026-09-21 10:30:10') AS t1, 51.043 AS lat_min, 55.394 AS lat_max, 22.221 AS lon_min, 25.902 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 09:30:10') AND t.position_timestamp < TIMESTAMP('2026-09-21 10:30:10') AND t.latitude BETWEEN 51.043 AND 55.394 AND t.longitude BETWEEN 22.221 AND 25.902))

