-- Steps between consecutive plots of one fused track that look wrong on a map or chart.
-- One scan of one fusion table for one UTC day. Filled in by find.py:
--   {table}    append_only_plots or fused_plots_aws
--   {day}      2026-09-22
--   {current}  TRUE for append, valid_to IS NULL for regular (only the latest version of each plot)
WITH plots AS (
  SELECT track_identifier AS tid, NULLIF(adshex, '') AS hex, NULLIF(callsign, '') AS cs,
         source_identifier AS src, UNIX_MICROS(position_timestamp) / 1e6 AS t,
         latitude AS lat, longitude AS lon, altitude_ft AS alt, ground_speed_kt AS gs
  FROM `{table}`
  WHERE DATE(position_timestamp) = '{day}' AND {current}
    AND track_identifier IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL
  -- one plot per track and time stamp
  QUALIFY ROW_NUMBER() OVER (PARTITION BY track_identifier, position_timestamp ORDER BY source_identifier) = 1
),

-- each plot with the one before and the one after in the same track
neighbours AS (
  SELECT *,
    LAG(t) OVER w AS pt, LAG(lat) OVER w AS plat, LAG(lon) OVER w AS plon,
    LAG(alt) OVER w AS palt, LAG(gs) OVER w AS pgs, LAG(src) OVER w AS psrc,
    LEAD(t) OVER w AS nt, LEAD(lat) OVER w AS nlat, LEAD(lon) OVER w AS nlon,
    COUNT(*) OVER (PARTITION BY tid) AS track_plots
  FROM plots WINDOW w AS (PARTITION BY tid ORDER BY t)
),

steps AS (
  SELECT *,
    t - pt AS dt,
    ST_DISTANCE(ST_GEOGPOINT(plon, plat), ST_GEOGPOINT(lon, lat)) AS dist_m,
    ST_DISTANCE(ST_GEOGPOINT(lon, lat), ST_GEOGPOINT(nlon, nlat)) AS next_dist_m,
    GREATEST(COALESCE(gs, 0), COALESCE(pgs, 0)) AS fast_gs,
    ST_AZIMUTH(ST_GEOGPOINT(plon, plat), ST_GEOGPOINT(lon, lat)) * 180 / ACOS(-1) AS heading_in,
    ST_AZIMUTH(ST_GEOGPOINT(lon, lat), ST_GEOGPOINT(nlon, nlat)) * 180 / ACOS(-1) AS heading_out
  FROM neighbours
  WHERE pt IS NOT NULL
    -- in the air: moving and above the ground, so parked aircraft and vehicles drop out
    AND GREATEST(COALESCE(gs, 0), COALESCE(pgs, 0)) >= 60
    AND GREATEST(COALESCE(alt, 0), COALESCE(palt, 0)) >= 500
),

events AS (
  -- position jump: moved at least 1.5 km further than its own ground speed allows
  SELECT 'position_jump' AS kind, *, dist_m - fast_gs * 0.514444 * dt AS size
  FROM steps
  WHERE dt BETWEEN 0.2 AND 120 AND dist_m - fast_gs * 0.514444 * dt > 1500

  UNION ALL
  -- altitude jump: at least 1,500 ft and faster than 6,000 ft per minute
  SELECT 'altitude_jump', *, ABS(alt - palt)
  FROM steps
  WHERE dt BETWEEN 0.2 AND 120 AND ABS(alt - palt) > 1500 AND ABS(alt - palt) / dt * 60 > 6000

  UNION ALL
  -- speed jump: reported ground speed changes by more than 120 kt within 20 s
  SELECT 'speed_jump', *, ABS(gs - pgs)
  FROM steps
  WHERE dt BETWEEN 0.2 AND 20 AND ABS(gs - pgs) > 120

  UNION ALL
  -- sharp turn: path direction changes more than 120 degrees at speed, both legs longer than 300 m
  SELECT 'sharp_turn', *,
    LEAST(ABS(heading_in - heading_out), 360 - ABS(heading_in - heading_out))
  FROM steps
  WHERE fast_gs >= 100 AND dt BETWEEN 0.2 AND 30 AND nt - t BETWEEN 0.2 AND 30
    AND dist_m > 300 AND next_dist_m > 300
)

SELECT kind, tid, hex, cs, src, psrc, t, pt, nt, lat, lon, plat, plon, nlat, nlon, alt, palt, gs, pgs,
       dt, dist_m, next_dist_m, size, track_plots,
       COUNT(*) OVER (PARTITION BY tid, kind) AS track_kind_events
FROM events
WHERE kind != 'sharp_turn' OR size > 120
-- keep at most 60 events per track and kind, so one broken track cannot fill the file
QUALIFY ROW_NUMBER() OVER (PARTITION BY tid, kind ORDER BY size DESC) <= 60
