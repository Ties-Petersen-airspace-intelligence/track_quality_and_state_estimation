
SELECT t.* FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021` t JOIN UNNEST([
    STRUCT('fw16-ryr7sn-2026-09-22' AS case_name, TIMESTAMP('2026-09-22 03:29:51') AS t0, TIMESTAMP('2026-09-22 04:29:51') AS t1, 51.326 AS lat_min, 57.131 AS lat_max, 10.102 AS lon_min, 21.96 AS lon_max)
  ]) c ON t.position_timestamp >= c.t0 AND t.position_timestamp < c.t1 AND t.common.latitude BETWEEN c.lat_min AND c.lat_max AND t.common.longitude BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.position_timestamp) = '2026-09-22'
  AND ((t.position_timestamp >= TIMESTAMP('2026-09-22 03:29:51') AND t.position_timestamp < TIMESTAMP('2026-09-22 04:29:51') AND t.common.latitude BETWEEN 51.326 AND 57.131 AND t.common.longitude BETWEEN 10.102 AND 21.96))

