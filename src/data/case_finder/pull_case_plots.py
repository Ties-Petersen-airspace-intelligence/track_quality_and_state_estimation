"""Pull the fused plots inside every case box so each case can be viewed.

usage: python pull_case_plots.py --day 2026-09-16 [--dry-run] [--only-unmarked]

One scan of the fused plots table for the day. Tracks involved in the hits come at
full resolution and from anywhere in the time window, not only inside the box; every other track in the box is thinned to one plot per 10 s as
context. Writes out/<day>/cases/<case id>.json.
"""
import argparse, json, pathlib

import bq

HERE = pathlib.Path(__file__).parent
COLS = ["case_id", "focus", "tid", "hex", "cs", "tail", "src", "t_us", "created_us", "valid_to_us",
        "lat", "lon", "alt", "gs", "hdg", "trk", "flight_id"]


def sql_for(day, cases):
    structs = []
    for c in cases:
        b = c["box"]
        tids = ", ".join(f"'{t}'" for t in c["focus_tids"]) or "''"
        hexes = ", ".join(f"'{h}'" for h in c["focus_hexes"]) or "''"
        structs.append(f"STRUCT('{c['id']}' AS case_id, {b['lat_min']} AS lat_min, {b['lat_max']} AS lat_max, "
                       f"{b['lon_min']} AS lon_min, {b['lon_max']} AS lon_max, TIMESTAMP('{c['t_start']}') AS t0, "
                       f"TIMESTAMP('{c['t_end']}') AS t1, [{tids}] AS tids, [{hexes}] AS hexes)")
    all_tids = sorted({t for c in cases for t in c["focus_tids"]}); all_hexes = sorted({h for c in cases for h in c["focus_hexes"]})
    tid_list = ", ".join(f"'{t}'" for t in all_tids) or "''"; hex_list = ", ".join(f"'{h}'" for h in all_hexes) or "''"
    lat_min = min(c["box"]["lat_min"] for c in cases); lat_max = max(c["box"]["lat_max"] for c in cases)
    lon_min = min(c["box"]["lon_min"] for c in cases); lon_max = max(c["box"]["lon_max"] for c in cases)
    return f"""
WITH cases AS (SELECT * FROM UNNEST([{",\n".join(structs)}])),
p AS (
  SELECT track_identifier AS tid, NULLIF(adshex, '') AS hex, NULLIF(callsign, '') AS cs, NULLIF(tail_number, '') AS tail,
         source_identifier AS src, position_timestamp AS t, created_at, valid_to, latitude AS lat, longitude AS lon,
         altitude_ft AS alt, ground_speed_kt AS gs, heading_deg AS hdg, track_deg AS trk, NULLIF(flight_plan_id, '') AS flight_id
  FROM `flyways.uni_track_provider.fused_plots_aws`
  WHERE DATE(position_timestamp) = '{day}'
    AND ((latitude BETWEEN {lat_min} AND {lat_max} AND longitude BETWEEN {lon_min} AND {lon_max})
         OR track_identifier IN ({tid_list}) OR adshex IN ({hex_list}))
),
tagged AS (
  SELECT c.case_id, (p.tid IN UNNEST(c.tids) OR p.hex IN UNNEST(c.hexes)) AS focus, p.*
  FROM p JOIN cases c
    ON p.t BETWEEN c.t0 AND c.t1
   AND ((p.lat BETWEEN c.lat_min AND c.lat_max AND p.lon BETWEEN c.lon_min AND c.lon_max) OR p.tid IN UNNEST(c.tids) OR p.hex IN UNNEST(c.hexes))
)
SELECT case_id, focus, tid, hex, cs, tail, src, UNIX_MICROS(t) AS t_us, UNIX_MICROS(created_at) AS created_us,
       UNIX_MICROS(valid_to) AS valid_to_us, lat, lon, alt, gs, hdg, trk, flight_id
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY case_id, tid, valid_to IS NULL, DIV(UNIX_SECONDS(t), 10) ORDER BY t) AS rn
  FROM tagged
)
WHERE focus OR rn = 1
ORDER BY case_id, t
"""


def num(v):
    if v in (None, ""):
        return None
    f = float(v)
    return int(f) if f == int(f) else f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only-unmarked", action="store_true", help="skip cases already marked good or bad")
    ap.add_argument("--missing", action="store_true", help="only cases that have no plots file yet")
    a = ap.parse_args()
    out = HERE / "out" / a.day
    cases = json.loads((out / "cases.json").read_text())
    if a.only_unmarked:
        cases = [c for c in cases if not c["mark"]]
    if a.missing:
        cases = [c for c in cases if not (out / "cases" / f"{c['id']}.json").exists()]
    if not cases:
        print("nothing to pull"); return
    sql = sql_for(a.day, cases)
    (out / "case_plots.sql").write_text(sql)
    if a.dry_run:
        bq.report_cost("case plots", sql)
        return
    rows = bq.run("case plots", sql)
    (out / "cases").mkdir(exist_ok=True)
    by_case = {}
    for r in rows:
        rec = [r["case_id"], r["focus"] == "true", r["tid"], r["hex"], r["cs"], r["tail"], int(r["src"]),
               int(r["t_us"]), num(r["created_us"]), num(r["valid_to_us"]), round(float(r["lat"]), 6), round(float(r["lon"]), 6),
               num(r["alt"]), num(r["gs"]), num(r["hdg"]), num(r["trk"]), r["flight_id"]]
        by_case.setdefault(r["case_id"], []).append(rec[1:])
    for c in cases:
        plots = by_case.get(c["id"], [])
        (out / "cases" / f"{c['id']}.json").write_text(json.dumps(dict(columns=COLS[1:], plots=plots)))
        print(f"{c['id']}: {len(plots)} plots, {sum(1 for p in plots if p[0])} on the tracks involved")


if __name__ == "__main__":
    main()
