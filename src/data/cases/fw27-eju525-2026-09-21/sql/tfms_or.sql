
SELECT t.* FROM `flyways.tfms_or_positions.tfms_or_positions` t JOIN UNNEST([
    STRUCT('fw27-eju525-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 19:10:44') AS t0, TIMESTAMP('2026-09-21 20:10:44') AS t1, 40.392 AS lat_min, 43.368 AS lat_max, 11.931 AS lon_min, 15.297 AS lon_max)
  ]) c ON t.common.position_timestamp >= c.t0 AND t.common.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.common.position_timestamp >= TIMESTAMP('2026-09-21 19:10:44') AND t.common.position_timestamp < TIMESTAMP('2026-09-21 20:10:44') AND t.common.latitude BETWEEN 40.392 AND 43.368 AND t.common.longitude BETWEEN 11.931 AND 15.297))

