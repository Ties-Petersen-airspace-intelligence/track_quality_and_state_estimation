-- how many of the uAvionix plots that carry only a geometric height made it into the production fused plots, one day
WITH geo_only AS (
  SELECT UPPER(common.adshex) AS adshex, position_timestamp
  FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
  WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16")
    AND flight_level IS NULL AND geometric_height IS NOT NULL
),
fused_uav AS (
  SELECT UPPER(adshex) AS adshex, position_timestamp, valid_to
  FROM `flyways.uni_track_provider.fused_plots_aws`
  WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16") AND source_identifier = 11
)
SELECT
  (SELECT COUNT(*) FROM geo_only) AS geo_only_raw,
  (SELECT COUNT(*) FROM fused_uav) AS fused_uav_rows,
  (SELECT COUNT(*) FROM fused_uav WHERE valid_to IS NULL) AS fused_uav_current,
  COUNT(*) AS geo_only_in_fused,
  COUNTIF(f.valid_to IS NULL) AS geo_only_in_fused_current,
  COUNT(DISTINCT g.adshex) AS geo_only_in_fused_aircraft
FROM geo_only g JOIN fused_uav f USING (adshex, position_timestamp)
