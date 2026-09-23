
SELECT t.* FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021` t JOIN UNNEST([
    STRUCT('fw25-igo955-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 16:15:26') AS t0, TIMESTAMP('2026-09-21 17:15:26') AS t1, 19.8 AS lat_min, 27.582 AS lat_max, 72.889 AS lon_min, 76.484 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 16:15:26') AND t.position_timestamp < TIMESTAMP('2026-09-21 17:15:26') AND t.common.latitude BETWEEN 19.8 AND 27.582 AND t.common.longitude BETWEEN 72.889 AND 76.484))

