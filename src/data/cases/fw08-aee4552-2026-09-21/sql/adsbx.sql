
SELECT t.* FROM `uni-adsbx-integration-master.adsbx_integration.adsbx_positions` t JOIN UNNEST([
    STRUCT('fw08-aee4552-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 06:02:42') AS t0, TIMESTAMP('2026-09-21 07:02:42') AS t1, 52.744 AS lat_min, 61.604 AS lat_max, 22.216 AS lon_min, 24.101 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 06:02:42') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 07:02:42') AND t.common.latitude BETWEEN 52.744 AND 61.604 AND t.common.longitude BETWEEN 22.216 AND 24.101))

