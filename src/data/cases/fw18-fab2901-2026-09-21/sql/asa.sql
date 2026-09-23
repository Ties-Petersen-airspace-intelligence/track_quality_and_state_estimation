
SELECT t.* FROM `flyways.asa_positions.asa_positions` t JOIN UNNEST([
    STRUCT('fw18-fab2901-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 00:05:58') AS t0, TIMESTAMP('2026-09-21 01:05:58') AS t1, -23.267 AS lat_min, -19.879 AS lat_max, -47.647 AS lon_min, -46.167 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 00:05:58') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 01:05:58') AND t.common.latitude BETWEEN -23.267 AND -19.879 AND t.common.longitude BETWEEN -47.647 AND -46.167))

