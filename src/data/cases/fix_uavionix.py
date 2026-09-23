"""Bring the uAvionix plots of a case in line with the fixed integration.

Two bugs in uni-track-source-uavionix were fixed on 22 September 2026, after the cases were pulled:
- common.altitude_ft held the geometric height; it is now flight_level * 100, the barometric altitude, with no fallback (#113, TS-1927)
- common.ground_speed_kt held NM/s; it is now knots, the raw value * 3600 (#114)

This rewrites uavionix.parquet in place and also the uAvionix plots that production copied into fusion_append.parquet
and fusion_final.parquet, matched to the raw plot by position time and hex. case.json records the fixes, so running
it again does nothing.

usage: uv run src/data/cases/fix_uavionix.py src/data/cases            # or one case folder
"""
from __future__ import annotations

import json, pathlib, sys

import pandas as pd

FIXES = ["uavionix altitude_ft = flight_level * 100 (TS-1927)", "uavionix ground_speed_kt = NM/s * 3600 (#114)"]
NM_PER_S_TO_KT = 3600.0
UAVIONIX_SOURCE_ID = "11"


def num(s):
    return pd.to_numeric(s, errors="coerce")


def as_text(values, fmt):
    """Back to the string columns the bq export uses; missing stays missing."""
    return pd.Series([None if pd.isna(v) else fmt(v) for v in values], index=values.index, dtype="string")


def fix_case(case: pathlib.Path) -> None:
    info = json.loads((case / "case.json").read_text())
    if info.get("fixes"):
        print(f"{case.name}: already fixed ({len(info['fixes'])} fixes recorded)")
        return
    raw_path = case / "uavionix.parquet"
    raw = pd.read_parquet(raw_path) if raw_path.exists() else pd.DataFrame()
    if raw.empty:
        print(f"{case.name}: no uAvionix plots, only recording the fixes")
    else:
        # the raw plots: barometric altitude and knots
        raw["common.altitude_ft"] = as_text(num(raw["flight_level"]) * 100, lambda v: str(int(round(v))))
        raw["common.ground_speed_kt"] = as_text(num(raw["common.ground_speed_kt"]) * NM_PER_S_TO_KT, lambda v: repr(float(v)))
        raw.to_parquet(raw_path, index=False)
        print(f"{case.name}: {len(raw)} raw plots rewritten, {raw['common.altitude_ft'].isna().sum()} without a flight level")

        # the copies production made of those plots, matched back to the raw plot
        lookup = raw.drop_duplicates(["position_timestamp_us", "common.adshex"]).set_index(["position_timestamp_us", "common.adshex"])
        for name in ["fusion_append", "fusion_final"]:
            f = pd.read_parquet(case / f"{name}.parquet")
            rows = f["source_identifier"] == UAVIONIX_SOURCE_ID
            if not rows.any():
                continue
            keys = list(zip(f.loc[rows, "position_timestamp_us"], f.loc[rows, "adshex"]))
            matched = [k in lookup.index for k in keys]
            altitude = pd.Series([lookup.at[k, "common.altitude_ft"] if ok else None for k, ok in zip(keys, matched)], index=f.index[rows], dtype="string")
            speed_raw = pd.Series([lookup.at[k, "common.ground_speed_kt"] if ok else None for k, ok in zip(keys, matched)], index=f.index[rows], dtype="string")
            speed_fallback = as_text(num(f.loc[rows, "ground_speed_kt"]) * NM_PER_S_TO_KT, lambda v: repr(float(v)))
            f.loc[rows, "altitude_ft"] = altitude
            f.loc[rows, "mean_sea_level_altitude_ft"] = altitude
            f.loc[rows, "ground_speed_kt"] = speed_raw.fillna(speed_fallback)
            f.to_parquet(case / f"{name}.parquet", index=False)
            print(f"  {name}: {int(rows.sum())} uAvionix plots rewritten, {sum(matched)} matched to a raw plot, {int(rows.sum()) - sum(matched)} took speed * 3600 and lost their altitude")
    info["fixes"] = FIXES
    (case / "case.json").write_text(json.dumps(info, indent=2) + "\n")


def main():
    paths = [pathlib.Path(p) for p in sys.argv[1:]] or [pathlib.Path("src/data/cases")]
    for p in paths:
        cases = [p] if (p / "case.json").exists() else sorted(q for q in p.iterdir() if (q / "case.json").exists())
        for case in cases:
            fix_case(case)


if __name__ == "__main__":
    main()
