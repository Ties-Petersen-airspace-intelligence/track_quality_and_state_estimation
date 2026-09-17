-- Find moments in one UTC day of fused output where today's fusion looks wrong.
-- One scan of the fused plots table for the day, selected columns only.
-- {day} is filled in by find_cases.py.  Timestamps come out as UNIX micros so the
-- bq JSON export does not round them to whole seconds.
WITH p AS (
  SELECT track_identifier AS tid, NULLIF(adshex, '') AS hex, NULLIF(callsign, '') AS cs,
         source_identifier AS src, position_timestamp AS t, latitude AS lat, longitude AS lon,
         altitude_ft AS alt, ground_speed_kt AS gs, created_at, valid_to
  FROM `flyways.uni_track_provider.fused_plots_aws`
  WHERE DATE(position_timestamp) = '{day}'
    AND latitude IS NOT NULL AND longitude IS NOT NULL AND track_identifier IS NOT NULL
),
cur AS (SELECT * FROM p WHERE valid_to IS NULL),
seq AS (
  SELECT *,
    LAG(t)   OVER w AS pt,  LAG(lat) OVER w AS plat, LAG(lon) OVER w AS plon,
    LAG(alt) OVER w AS palt, LAG(src) OVER w AS psrc, LAG(gs) OVER w AS pgs,
    LAG(t, 2) OVER w AS ppt, LAG(lat, 2) OVER w AS pplat, LAG(lon, 2) OVER w AS pplon, LAG(src, 2) OVER w AS ppsrc
  FROM cur WINDOW w AS (PARTITION BY tid ORDER BY t)
),
step AS (
  SELECT *,
    TIMESTAMP_DIFF(t, pt, MILLISECOND) / 1000.0 AS dt,
    ST_DISTANCE(ST_GEOGPOINT(lon, lat), ST_GEOGPOINT(plon, plat)) AS dist_m
  FROM seq WHERE pt IS NOT NULL
),
-- 1. jump: implied speed between two consecutive plots of one track above 1500 kt
jump AS (
  SELECT 'jump' AS rule, tid, hex, cs, src, t, lat, lon, alt, gs,
    dist_m / dt * 1.943844 AS metric, dt AS dt_s, dist_m, palt, psrc, pgs, CAST(NULL AS STRING) AS n, plat, plon
  FROM step WHERE dt BETWEEN 0.5 AND 600 AND dist_m > 2000 AND dist_m / dt * 1.943844 > 1500
),
-- 4. altitude spike: more than 10,000 ft/min between consecutive plots and at least 2,000 ft
altspike AS (
  SELECT 'altitude_spike' AS rule, tid, hex, cs, src, t, lat, lon, alt, gs,
    ABS(alt - palt) AS metric, dt AS dt_s, dist_m, palt, psrc, pgs, CAST(NULL AS STRING) AS n, plat, plon
  FROM step WHERE dt >= 1 AND alt IS NOT NULL AND palt IS NOT NULL AND ABS(alt - palt) > 2000 AND ABS(alt - palt) / dt * 60 > 10000
),
-- 5. gap and reappear: more than 10 minutes without a plot, then the track reappears faster than 650 kt could explain
gap AS (
  SELECT 'gap_reappear' AS rule, tid, hex, cs, src, t, lat, lon, alt, gs,
    dist_m / dt * 1.943844 AS metric, dt AS dt_s, dist_m, palt, psrc, pgs, CAST(NULL AS STRING) AS n, plat, plon
  FROM step WHERE dt > 600 AND dist_m / dt * 1.943844 > 650
),
-- 6. zigzag between sources: middle plot from another source than its neighbours, more than 300 m off the line between them, all within 30 s
zigzag AS (
  SELECT 'source_zigzag' AS rule, tid, hex, cs, psrc AS src, pt AS t, plat AS lat, plon AS lon, palt AS alt, pgs AS gs,
    ST_DISTANCE(ST_GEOGPOINT(plon, plat), ST_MAKELINE(ST_GEOGPOINT(pplon, pplat), ST_GEOGPOINT(lon, lat))) AS metric,
    TIMESTAMP_DIFF(t, ppt, MILLISECOND) / 1000.0 AS dt_s, ST_DISTANCE(ST_GEOGPOINT(pplon, pplat), ST_GEOGPOINT(lon, lat)) AS dist_m, alt AS palt, src AS psrc, pgs, CAST(NULL AS STRING) AS n, pplat AS plat, pplon AS plon
  FROM seq
  WHERE ppt IS NOT NULL AND psrc != src AND psrc != ppsrc AND src = ppsrc
    AND TIMESTAMP_DIFF(t, ppt, SECOND) BETWEEN 1 AND 30
    AND ST_DISTANCE(ST_GEOGPOINT(pplon, pplat), ST_GEOGPOINT(lon, lat)) > 200
    AND ST_DISTANCE(ST_GEOGPOINT(plon, plat), ST_MAKELINE(ST_GEOGPOINT(pplon, pplat), ST_GEOGPOINT(lon, lat))) > 300
),
-- 2. recorrelation: the same hex shows up under a different track id within 10 minutes
byhex AS (
  SELECT *, LAG(tid) OVER w AS ptid, LAG(t) OVER w AS pt, LAG(lat) OVER w AS plat, LAG(lon) OVER w AS plon
  FROM cur WHERE hex IS NOT NULL WINDOW w AS (PARTITION BY hex ORDER BY t)
),
recorr AS (
  SELECT 'recorrelation' AS rule, tid, hex, cs, src, t, lat, lon, alt, gs,
    ST_DISTANCE(ST_GEOGPOINT(lon, lat), ST_GEOGPOINT(plon, plat)) AS metric, TIMESTAMP_DIFF(t, pt, MILLISECOND) / 1000.0 AS dt_s,
    ST_DISTANCE(ST_GEOGPOINT(lon, lat), ST_GEOGPOINT(plon, plat)) AS dist_m, NULL AS palt, NULL AS psrc, NULL AS pgs, ptid AS n, plat, plon
  FROM byhex WHERE ptid IS NOT NULL AND ptid != tid AND TIMESTAMP_DIFF(t, pt, SECOND) BETWEEN 0 AND 600
),
-- 3. rewritten past: plots replaced by a later rewrite more than 10 minutes after their own time, counted per track per 10 minute block
rewritten AS (
  SELECT 'rewritten_past' AS rule, tid, ANY_VALUE(hex) AS hex, ANY_VALUE(cs) AS cs, ANY_VALUE(src) AS src,
    MIN(t) AS t, ANY_VALUE(lat) AS lat, ANY_VALUE(lon) AS lon, ANY_VALUE(alt) AS alt, ANY_VALUE(gs) AS gs,
    COUNT(*) AS metric, MAX(TIMESTAMP_DIFF(valid_to, t, SECOND)) AS dt_s, NULL AS dist_m, NULL AS palt, NULL AS psrc, NULL AS pgs,
    CAST(COUNT(*) AS STRING) AS n, NULL AS plat, NULL AS plon
  FROM p WHERE valid_to IS NOT NULL AND TIMESTAMP_DIFF(valid_to, t, SECOND) > 600
  GROUP BY tid, TIMESTAMP_TRUNC(t, HOUR), DIV(EXTRACT(MINUTE FROM t), 10)
  HAVING COUNT(*) >= 20
),
allhits AS (
  SELECT * FROM jump UNION ALL SELECT * FROM altspike UNION ALL SELECT * FROM gap
  UNION ALL SELECT * FROM zigzag UNION ALL SELECT * FROM recorr UNION ALL SELECT * FROM rewritten
)
SELECT rule, tid, hex, cs, src, UNIX_MICROS(t) AS t_us, lat, lon, alt, gs, metric, dt_s, dist_m, palt, psrc, pgs, n, plat, plon,
       COUNT(*) OVER (PARTITION BY rule) AS rule_total
FROM allhits
QUALIFY ROW_NUMBER() OVER (PARTITION BY rule, tid ORDER BY metric DESC) <= 3
   AND ROW_NUMBER() OVER (PARTITION BY rule ORDER BY metric DESC) <= 600
ORDER BY rule, metric DESC
