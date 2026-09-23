
SELECT t.* FROM `flyways.uni_track_provider.fused_plots_aws` t JOIN UNNEST([
    STRUCT('fw07-iaw2-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 08:12:01') AS t0, TIMESTAMP('2026-09-21 09:12:01') AS t1, 59.65 AS lat_min, 64.117 AS lat_max, 4.099 AS lon_min, 12.228 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 08:12:01') AND t.position_timestamp < TIMESTAMP('2026-09-21 09:12:01') AND t.latitude BETWEEN 59.65 AND 64.117 AND t.longitude BETWEEN 4.099 AND 12.228))

