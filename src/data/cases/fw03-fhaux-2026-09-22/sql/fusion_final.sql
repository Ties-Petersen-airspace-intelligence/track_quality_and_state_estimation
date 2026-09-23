
SELECT t.* FROM `flyways.uni_track_provider.fused_plots_aws` t JOIN UNNEST([
    STRUCT('fw03-fhaux-2026-09-22' AS case_name, TIMESTAMP('2026-09-22 07:47:42') AS t0, TIMESTAMP('2026-09-22 08:47:42') AS t1, 44.896 AS lat_min, 47.562 AS lat_max, 4.961 AS lon_min, 6.958 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-22'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-22 07:47:42') AND t.position_timestamp < TIMESTAMP('2026-09-22 08:47:42') AND t.latitude BETWEEN 44.896 AND 47.562 AND t.longitude BETWEEN 4.961 AND 6.958))

