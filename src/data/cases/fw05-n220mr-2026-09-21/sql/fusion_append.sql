
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw05-n220mr-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 05:32:21') AS t0, TIMESTAMP('2026-09-21 06:32:21') AS t1, 59.479 AS lat_min, 61.221 AS lat_max, 10.502 AS lon_min, 13.319 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 05:32:21') AND t.position_timestamp < TIMESTAMP('2026-09-21 06:32:21') AND t.latitude BETWEEN 59.479 AND 61.221 AND t.longitude BETWEEN 10.502 AND 13.319))

