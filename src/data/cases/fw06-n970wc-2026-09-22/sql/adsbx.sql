
SELECT t.* FROM `uni-adsbx-integration-master.adsbx_integration.adsbx_positions` t JOIN UNNEST([
    STRUCT('fw06-n970wc-2026-09-22' AS case_name, TIMESTAMP('2026-09-22 00:18:55') AS t0, TIMESTAMP('2026-09-22 01:18:55') AS t1, 39.691 AS lat_min, 41.145 AS lat_max, -112.514 AS lon_min, -111.186 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-22'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-22 00:18:55') AND t.common.position_timestamp < TIMESTAMP('2026-09-22 01:18:55') AND t.common.latitude BETWEEN 39.691 AND 41.145 AND t.common.longitude BETWEEN -112.514 AND -111.186))

