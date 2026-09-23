
SELECT t.* FROM `uni-adsbx-integration-master.adsbx_integration.adsbx_positions` t JOIN UNNEST([
    STRUCT('fw12-arg1708-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 10:16:50') AS t0, TIMESTAMP('2026-09-21 11:16:50') AS t1, -35.044 AS lat_min, -32.962 AS lat_max, -60.371 AS lon_min, -57.879 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 10:16:50') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 11:16:50') AND t.common.latitude BETWEEN -35.044 AND -32.962 AND t.common.longitude BETWEEN -60.371 AND -57.879))

