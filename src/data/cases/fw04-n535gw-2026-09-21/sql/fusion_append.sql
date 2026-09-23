
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw04-n535gw-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 14:52:17') AS t0, TIMESTAMP('2026-09-21 15:52:17') AS t1, 37.931 AS lat_min, 39.667 AS lat_max, -108.397 AS lon_min, -105.212 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 14:52:17') AND t.position_timestamp < TIMESTAMP('2026-09-21 15:52:17') AND t.latitude BETWEEN 37.931 AND 39.667 AND t.longitude BETWEEN -108.397 AND -105.212))

