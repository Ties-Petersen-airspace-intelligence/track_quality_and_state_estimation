
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw27-eju525-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 19:10:44') AS t0, TIMESTAMP('2026-09-21 20:10:44') AS t1, 40.392 AS lat_min, 43.368 AS lat_max, 11.931 AS lon_min, 15.297 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 19:10:44') AND t.position_timestamp < TIMESTAMP('2026-09-21 20:10:44') AND t.latitude BETWEEN 40.392 AND 43.368 AND t.longitude BETWEEN 11.931 AND 15.297))

