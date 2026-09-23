
SELECT t.* FROM `flyways.planefinder_positions.planefinder_positions` t JOIN UNNEST([
    STRUCT('fw26-rtv2-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 10:41:06') AS t0, TIMESTAMP('2026-09-21 11:41:06') AS t1, 40.751 AS lat_min, 42.054 AS lat_max, -9.302 AS lon_min, -7.912 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.pos_update_time) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 10:41:06') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 11:41:06') AND t.common.latitude BETWEEN 40.751 AND 42.054 AND t.common.longitude BETWEEN -9.302 AND -7.912))

