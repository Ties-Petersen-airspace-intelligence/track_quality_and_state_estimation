
SELECT t.* FROM `flyways-aws-prod.uni_track_source_stdds.uni_track_source_stdds_position_reports` t JOIN UNNEST([
    STRUCT('fw14-fgmqh-2026-09-22' AS case_name, TIMESTAMP('2026-09-22 09:48:49') AS t0, TIMESTAMP('2026-09-22 10:48:49') AS t1, 44.556 AS lat_min, 45.865 AS lat_max, 4.321 AS lon_min, 5.847 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-22'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-22 09:48:49') AND t.position_timestamp < TIMESTAMP('2026-09-22 10:48:49') AND t.common.latitude BETWEEN 44.556 AND 45.865 AND t.common.longitude BETWEEN 4.321 AND 5.847))

