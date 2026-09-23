-- Which events to download, from the steps query or a saved result of it.
-- uAvionix altitude and speed jumps are one known cause each (GPS height, speed in NM/s),
-- so only the biggest few hundred of those are kept.
SELECT * EXCEPT (rank_in_kind) FROM (
  SELECT *, IF((src = 11 OR psrc = 11) AND kind IN ('altitude_jump', 'speed_jump'), CONCAT(kind, '_uavionix'), kind) AS kind_group,
         ROW_NUMBER() OVER (PARTITION BY IF((src = 11 OR psrc = 11) AND kind IN ('altitude_jump', 'speed_jump'), CONCAT(kind, '_uavionix'), kind)
                            ORDER BY size DESC) AS rank_in_kind
  FROM ({events})
)
WHERE (kind = 'position_jump' AND size > 2500)
   OR (kind = 'sharp_turn' AND dist_m > 1000 AND ST_DISTANCE(ST_GEOGPOINT(lon, lat), ST_GEOGPOINT(nlon, nlat)) > 1000)
   OR (kind_group = 'altitude_jump' AND size > 2500)
   OR (kind_group = 'speed_jump' AND size > 200)
   OR (kind_group IN ('altitude_jump_uavionix', 'speed_jump_uavionix') AND rank_in_kind <= 300)
