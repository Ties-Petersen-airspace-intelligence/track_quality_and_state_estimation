-- height histogram of the geometric-only uAvionix plots, 500 ft bins, split by the on-ground bit
SELECT CAST(FLOOR(geometric_height / 500) * 500 AS INT64) AS height_bin, target_report_descriptor.is_ground_bit_set AS ground_bit, COUNT(*) AS n
FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16") AND flight_level IS NULL AND geometric_height IS NOT NULL
GROUP BY height_bin, ground_bit ORDER BY height_bin
