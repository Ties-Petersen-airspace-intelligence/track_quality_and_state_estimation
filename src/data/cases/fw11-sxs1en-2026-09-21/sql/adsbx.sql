
SELECT t.* FROM `uni-adsbx-integration-master.adsbx_integration.adsbx_positions` t JOIN UNNEST([
    STRUCT('fw11-sxs1en-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 21:32:23') AS t0, TIMESTAMP('2026-09-21 22:32:23') AS t1, 52.146 AS lat_min, 56.132 AS lat_max, 12.137 AS lon_min, 18.157 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 21:32:23') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 22:32:23') AND t.common.latitude BETWEEN 52.146 AND 56.132 AND t.common.longitude BETWEEN 12.137 AND 18.157))

