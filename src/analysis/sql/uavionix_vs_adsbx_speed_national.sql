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
j AS (SELECT * FROM u JOIN a USING (hex, ts) WHERE gs_u > 0)
SELECT
  CASE WHEN lat BETWEEN 15 AND 75 AND lon BETWEEN -170 AND -50 THEN 'North America'
       WHEN lat BETWEEN 35 AND 72 AND lon BETWEEN -25 AND 45 THEN 'Europe' ELSE 'other' END AS region,
  COUNT(*) AS pairs, COUNT(DISTINCT hex) AS aircraft,
  APPROX_QUANTILES(gs_a / gs_u, 100)[OFFSET(10)] AS ratio_p10,
  APPROX_QUANTILES(gs_a / gs_u, 100)[OFFSET(50)] AS ratio_p50,
  APPROX_QUANTILES(gs_a / gs_u, 100)[OFFSET(90)] AS ratio_p90,
  APPROX_QUANTILES(ABS(gs_u * 3600 - gs_a), 100)[OFFSET(50)] AS diff_after_x3600_p50_kt,
  APPROX_QUANTILES(ABS(gs_u * 3600 - gs_a), 100)[OFFSET(90)] AS diff_after_x3600_p90_kt
FROM j GROUP BY region ORDER BY pairs DESC
