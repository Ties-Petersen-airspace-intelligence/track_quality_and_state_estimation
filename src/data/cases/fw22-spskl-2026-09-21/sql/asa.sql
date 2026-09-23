
SELECT t.* FROM `flyways.asa_positions.asa_positions` t JOIN UNNEST([
    STRUCT('fw22-spskl-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 07:36:17') AS t0, TIMESTAMP('2026-09-21 08:36:17') AS t1, 50.111 AS lat_min, 51.157 AS lat_max, 19.321 AS lon_min, 21.152 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 07:36:17') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 08:36:17') AND t.common.latitude BETWEEN 50.111 AND 51.157 AND t.common.longitude BETWEEN 19.321 AND 21.152))

