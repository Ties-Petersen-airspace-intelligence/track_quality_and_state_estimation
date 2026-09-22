-- one day, all coverage: uAvionix ground speed against ADS-B Exchange for the same aircraft in the same second
WITH u AS (
  SELECT UPPER(common.adshex) AS hex, TIMESTAMP_TRUNC(position_timestamp, SECOND) AS ts,
         common.ground_speed_kt AS gs_u, common.latitude AS lat, common.longitude AS lon
  FROM `flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021`
  WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16") AND common.ground_speed_kt IS NOT NULL
),
a AS (
  SELECT UPPER(common.adshex) AS hex, TIMESTAMP_TRUNC(position_timestamp, SECOND) AS ts, common.ground_speed_kt AS gs_a
  FROM `uni-adsbx-integration-master.adsbx_integration.adsbx_positions`
  WHERE TIMESTAMP_TRUNC(position_timestamp, DAY) = TIMESTAMP("2026-09-16") AND common.ground_speed_kt > 30
),
j AS (SELECT * FROM u JOIN a USING (hex, ts) WHERE gs_u > 0 AND MOD(ABS(FARM_FINGERPRINT(CONCAT(hex, CAST(ts AS STRING)))), 20000) = 0)
SELECT hex, ts, gs_u, gs_a, lat, lon FROM j
