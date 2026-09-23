
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw23-n2122z-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 22:55:57') AS t0, TIMESTAMP('2026-09-21 23:55:57') AS t1, 34.137 AS lat_min, 35.436 AS lat_max, -112.969 AS lon_min, -111.675 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 22:55:57') AND t.position_timestamp < TIMESTAMP('2026-09-21 23:55:57') AND t.latitude BETWEEN 34.137 AND 35.436 AND t.longitude BETWEEN -112.969 AND -111.675))

