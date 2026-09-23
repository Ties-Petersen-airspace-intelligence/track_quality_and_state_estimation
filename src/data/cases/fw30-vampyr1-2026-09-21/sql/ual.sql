
SELECT t.* FROM `flyways.ual_integration.ual_positions` t JOIN UNNEST([
    STRUCT('fw30-vampyr1-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 19:00:06') AS t0, TIMESTAMP('2026-09-21 20:00:06') AS t1, 30.907 AS lat_min, 33.016 AS lat_max, -115.287 AS lon_min, -109.754 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.source_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 19:00:06') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 20:00:06') AND t.common.latitude BETWEEN 30.907 AND 33.016 AND t.common.longitude BETWEEN -115.287 AND -109.754))

