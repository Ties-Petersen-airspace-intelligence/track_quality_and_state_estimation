
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw11-sxs1en-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 21:32:23') AS t0, TIMESTAMP('2026-09-21 22:32:23') AS t1, 52.146 AS lat_min, 56.132 AS lat_max, 12.137 AS lon_min, 18.157 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 21:32:23') AND t.position_timestamp < TIMESTAMP('2026-09-21 22:32:23') AND t.latitude BETWEEN 52.146 AND 56.132 AND t.longitude BETWEEN 12.137 AND 18.157))

