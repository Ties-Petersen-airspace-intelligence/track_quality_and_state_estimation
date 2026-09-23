
SELECT t.* FROM `flyways.asa_positions.asa_positions` t JOIN UNNEST([
    STRUCT('fw09-cmp886-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 00:12:43') AS t0, TIMESTAMP('2026-09-21 01:12:43') AS t1, 8.328 AS lat_min, 11.796 AS lat_max, -79.854 AS lon_min, -72.352 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 00:12:43') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 01:12:43') AND t.common.latitude BETWEEN 8.328 AND 11.796 AND t.common.longitude BETWEEN -79.854 AND -72.352))

