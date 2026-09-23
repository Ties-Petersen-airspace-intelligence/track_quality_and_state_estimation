
SELECT t.* FROM `flyways-aws-prod.uni_track_source_stdds.uni_track_source_stdds_position_reports` t JOIN UNNEST([
    STRUCT('fw17-lpe2391-2026-09-22' AS case_name, TIMESTAMP('2026-09-22 00:39:27') AS t0, TIMESTAMP('2026-09-22 01:39:27') AS t1, -12.521 AS lat_min, -4.833 AS lat_max, -77.813 AS lon_min, -75.731 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-22'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-22 00:39:27') AND t.position_timestamp < TIMESTAMP('2026-09-22 01:39:27') AND t.common.latitude BETWEEN -12.521 AND -4.833 AND t.common.longitude BETWEEN -77.813 AND -75.731))

