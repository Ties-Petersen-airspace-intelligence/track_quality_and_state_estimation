"""Step 3: pull the fused plots around every candidate from both fusion tables.

usage: uv run data/visible_error_finder/pull.py --day 2026-09-22 [--dry-run] [--set regular_spikes]

Reads out/<day>/candidates.parquet, writes out/<day>/plots.parquet with one row per plot,
a column fusion (append or regular) and the candidate id. Run from src/.
Append and regular fusion use different track ids (append uses the hex address), so plots
are matched on the candidate's track id or its hex address.
"""
import argparse, pathlib

import pandas as pd

import bq
from sets import SETS, path

HERE = pathlib.Path(__file__).parent
TABLES = {
    "append": ("flyways-aws-prod.uni_track_fusion.append_only_plots", "TRUE"),
    "regular": ("flyways.uni_track_provider.fused_plots_aws", "valid_to IS NULL"),
}


def hex_literal(value) -> str:
    return "CAST(NULL AS STRING)" if pd.isna(value) else f"'{value}'"


def windows_sql(candidates: pd.DataFrame) -> str:
    rows = ",\n    ".join(
        f"STRUCT('{c.id}' AS id, '{c.tid}' AS tid, {hex_literal(c.hex)} AS hex, {c.t0:.3f} AS t0, {c.t1:.3f} AS t1)"
        for c in candidates.itertuples())
    return f"UNNEST([\n    {rows}\n  ])"


def plots_sql(day: str, candidates: pd.DataFrame) -> str:
    tids = ", ".join(f"'{tid}'" for tid in sorted(candidates.tid.unique()))
    hexes = ", ".join(f"'{h}'" for h in sorted(candidates.hex.dropna().unique())) or "''"
    parts = []
    for name, (table, current) in TABLES.items():
        parts.append(f"""
  SELECT '{name}' AS fusion, track_identifier AS tid, NULLIF(adshex, '') AS hex, NULLIF(callsign, '') AS cs,
         source_identifier AS src, UNIX_MICROS(position_timestamp) / 1e6 AS t,
         latitude AS lat, longitude AS lon, altitude_ft AS alt, ground_speed_kt AS gs, track_deg AS trk
  FROM `{table}`
  WHERE DATE(position_timestamp) = '{day}' AND {current} AND (track_identifier IN ({tids}) OR adshex IN ({hexes}))""")
    return f"""
WITH windows AS (SELECT * FROM {windows_sql(candidates)}),
plots AS ({" UNION ALL ".join(parts)}
)
SELECT w.id, p.* FROM plots p JOIN windows w ON (p.tid = w.tid OR p.hex = w.hex) AND p.t BETWEEN w.t0 AND w.t1
ORDER BY w.id, p.fusion, p.t
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--set", default="", choices=SETS)
    args = parser.parse_args()
    out = HERE / "out" / args.day
    candidates = pd.read_parquet(path(out, "candidates", args.set))
    sql = plots_sql(args.day, candidates)
    path(out, "plots", args.set, ".sql").write_text(sql)

    # cost first
    gigabytes, dollars = bq.cost(sql)
    print(f"plots {args.day}: {len(candidates)} candidates, {gigabytes:.1f} GB, ${dollars:.2f}")
    if args.dry_run:
        return

    plots = bq.run(sql)
    plots.to_parquet(path(out, "plots", args.set))
    print(f"  {len(plots)} plots")


if __name__ == "__main__":
    main()
