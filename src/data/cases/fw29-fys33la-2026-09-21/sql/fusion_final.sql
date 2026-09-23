
SELECT t.* FROM `flyways.uni_track_provider.fused_plots_aws` t JOIN UNNEST([
    STRUCT('fw29-fys33la-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 12:01:44') AS t0, TIMESTAMP('2026-09-21 13:01:44') AS t1, 39.773 AS lat_min, 41.592 AS lat_max, -4.76 AS lon_min, -3.254 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 12:01:44') AND t.position_timestamp < TIMESTAMP('2026-09-21 13:01:44') AND t.latitude BETWEEN 39.773 AND 41.592 AND t.longitude BETWEEN -4.76 AND -3.254))

