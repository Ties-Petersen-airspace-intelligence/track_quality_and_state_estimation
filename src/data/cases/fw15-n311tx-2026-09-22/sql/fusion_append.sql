
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw15-n311tx-2026-09-22' AS case_name, TIMESTAMP('2026-09-22 00:39:09') AS t0, TIMESTAMP('2026-09-22 01:39:09') AS t1, 31.321 AS lat_min, 33.177 AS lat_max, -97.367 AS lon_min, -95.07 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-22'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-22 00:39:09') AND t.position_timestamp < TIMESTAMP('2026-09-22 01:39:09') AND t.latitude BETWEEN 31.321 AND 33.177 AND t.longitude BETWEEN -97.367 AND -95.07))

