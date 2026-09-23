
SELECT t.* FROM `flyways.ual_integration.ual_positions` t JOIN UNNEST([
    STRUCT('fw24-nak276-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 09:16:04') AS t0, TIMESTAMP('2026-09-21 10:16:04') AS t1, 42.798 AS lat_min, 44.336 AS lat_max, 0.18 AS lon_min, 2.417 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.source_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 09:16:04') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 10:16:04') AND t.common.latitude BETWEEN 42.798 AND 44.336 AND t.common.longitude BETWEEN 0.18 AND 2.417))

