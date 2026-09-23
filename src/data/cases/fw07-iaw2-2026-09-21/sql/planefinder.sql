
SELECT t.* FROM `flyways.planefinder_positions.planefinder_positions` t JOIN UNNEST([
    STRUCT('fw07-iaw2-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 08:12:01') AS t0, TIMESTAMP('2026-09-21 09:12:01') AS t1, 59.65 AS lat_min, 64.117 AS lat_max, 4.099 AS lon_min, 12.228 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.pos_update_time) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 08:12:01') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 09:12:01') AND t.common.latitude BETWEEN 59.65 AND 64.117 AND t.common.longitude BETWEEN 4.099 AND 12.228))

