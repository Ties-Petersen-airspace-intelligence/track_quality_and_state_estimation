
SELECT t.* FROM `flyways.planefinder_positions.planefinder_positions` t JOIN UNNEST([
    STRUCT('fw19-fhdgq1-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 15:01:29') AS t0, TIMESTAMP('2026-09-21 16:01:29') AS t1, 39.848 AS lat_min, 42.011 AS lat_max, -5.253 AS lon_min, -3.252 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.pos_update_time) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 15:01:29') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 16:01:29') AND t.common.latitude BETWEEN 39.848 AND 42.011 AND t.common.longitude BETWEEN -5.253 AND -3.252))

