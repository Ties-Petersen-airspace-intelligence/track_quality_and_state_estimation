
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw13-qtr8954-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 16:06:05') AS t0, TIMESTAMP('2026-09-21 17:06:05') AS t1, 24.255 AS lat_min, 25.933 AS lat_max, 51.106 AS lon_min, 57.551 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 16:06:05') AND t.position_timestamp < TIMESTAMP('2026-09-21 17:06:05') AND t.latitude BETWEEN 24.255 AND 25.933 AND t.longitude BETWEEN 51.106 AND 57.551))

