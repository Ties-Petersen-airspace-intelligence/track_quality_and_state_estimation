-- the gap between geometric height and flight level by height band, whole day, all of uAvionix coverage
SELECT
  CASE WHEN flight_level * 100 < 5000 THEN 'a <5k' WHEN flight_level * 100 < 15000 THEN 'b 5-15k' WHEN flight_level * 100 < 25000 THEN 'c 15-25k'
       WHEN flight_level * 100 < 35000 THEN 'd 25-35k' ELSE 'e >35k' END AS band,
  COUNT(*) AS n,
  APPROX_QUANTILES(geometric_height - flight_level * 100, 100)[OFFSET(10)] AS gap_p10,
  APPROX_QUANTILES(geometric_height - flight_level * 100, 100)[OFFSET(50)] AS gap_p50,
  APPROX_QUANTILES(geometric_height - flight_level * 100, 100)[OFFSET(90)] AS gap_p90
FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16") AND geometric_height IS NOT NULL AND flight_level IS NOT NULL
GROUP BY band ORDER BY band
