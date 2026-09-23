
SELECT t.* FROM `flyways-aws-prod.uni_track_fusion.append_only_plots` t JOIN UNNEST([
    STRUCT('fw28-n7407w-2026-09-22' AS case_name, TIMESTAMP('2026-09-22 01:46:49') AS t0, TIMESTAMP('2026-09-22 02:46:49') AS t1, 39.69 AS lat_min, 40.752 AS lat_max, -112.269 AS lon_min, -111.193 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.latitude BETWEEN c.lat_min AND c.lat_max AND t.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-22'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-22 01:46:49') AND t.position_timestamp < TIMESTAMP('2026-09-22 02:46:49') AND t.latitude BETWEEN 39.69 AND 40.752 AND t.longitude BETWEEN -112.269 AND -111.193))

