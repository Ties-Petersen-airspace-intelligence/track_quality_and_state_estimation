
SELECT t.* FROM `flyways.tfms_ti_positions.tfms_ti_positions` t JOIN UNNEST([
    STRUCT('fw23-n2122z-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 22:55:57') AS t0, TIMESTAMP('2026-09-21 23:55:57') AS t1, 34.137 AS lat_min, 35.436 AS lat_max, -112.969 AS lon_min, -111.675 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 22:55:57') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 23:55:57') AND t.common.latitude BETWEEN 34.137 AND 35.436 AND t.common.longitude BETWEEN -112.969 AND -111.675))

