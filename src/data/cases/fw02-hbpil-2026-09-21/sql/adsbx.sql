
SELECT t.* FROM `uni-adsbx-integration-master.adsbx_integration.adsbx_positions` t JOIN UNNEST([
    STRUCT('fw02-hbpil-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 14:52:58') AS t0, TIMESTAMP('2026-09-21 15:52:58') AS t1, 45.763 AS lat_min, 47.09 AS lat_max, 4.349 AS lon_min, 7.408 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 14:52:58') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 15:52:58') AND t.common.latitude BETWEEN 45.763 AND 47.09 AND t.common.longitude BETWEEN 4.349 AND 7.408))

