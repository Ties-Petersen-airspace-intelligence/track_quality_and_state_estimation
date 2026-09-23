
SELECT t.* FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021` t JOIN UNNEST([
    STRUCT('fw10-rsx324-2026-09-21' AS case_name, TIMESTAMP('2026-09-21 02:39:14') AS t0, TIMESTAMP('2026-09-21 03:39:14') AS t1, 46.228 AS lat_min, 54.056 AS lat_max, 21.362 AS lon_min, 23.169 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-21'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-21 02:39:14') AND t.position_timestamp < TIMESTAMP('2026-09-21 03:39:14') AND t.common.latitude BETWEEN 46.228 AND 54.056 AND t.common.longitude BETWEEN 21.362 AND 23.169))

