
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw19-fhdgq1-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 15:01:29') AS t0, TIMESTAMP('2026-09-21 16:01:29') AS t1, 39.848 AS lat_min, 42.011 AS lat_max, -5.253 AS lon_min, -3.252 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 15:01:29') AND t.position_timestamp < TIMESTAMP('2026-09-21 16:01:29') AND t.latitude BETWEEN 39.848 AND 42.011 AND t.longitude BETWEEN -5.253 AND -3.252))

