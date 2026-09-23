
SELECT t.* FROM `flyways.uni_track_provider.fused_plots_aws` t JOIN UNNEST([
    STRUCT('fw20-n998m-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 15:54:52') AS t0, TIMESTAMP('2026-09-21 16:54:52') AS t1, 39.81 AS lat_min, 41.278 AS lat_max, -107.801 AS lon_min, -106.497 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 15:54:52') AND t.position_timestamp < TIMESTAMP('2026-09-21 16:54:52') AND t.latitude BETWEEN 39.81 AND 41.278 AND t.longitude BETWEEN -107.801 AND -106.497))

