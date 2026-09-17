"""Turn the production fusion tables of a case into runs, so the viewer can replay them like a strategy.

usage: uv run -m harness.production --case data/cases/<name>

runs/prod_fusion_append: what production's append path first emitted (append_only_plots). Rows are never
invalidated, the table has no such column, so every plot stays.
runs/prod_fusion_regular: production's result after the regular and recorrelation rewrites, from the provider
table (fused_plots_aws), with created_at and valid_to as
BigQuery holds them, so rewrites replace the past exactly as consumers saw it.
"""
from __future__ import annotations

import argparse, pathlib

import pandas as pd

SOURCE_TRACK_KEY = "track_identifier"


def num(series, kind="Float64"):
    return pd.to_numeric(series, errors="coerce").astype(kind)


def common_columns(f: pd.DataFrame, created: str, position: str) -> pd.DataFrame:
    return pd.DataFrame(dict(
        created_at_us=num(f[created], "Int64"), position_us=num(f[position], "Int64"),
        source_received_us=num(f["source_received_timestamp_us"], "Int64"), asi_received_us=num(f["asi_received_timestamp_us"], "Int64"),
        source_identifier=num(f["source_identifier"], "Int64"), source_track_identifier=f[SOURCE_TRACK_KEY],
        latitude=num(f["latitude"]), longitude=num(f["longitude"]),
        altitude_ft=num(f["altitude_ft"]), ground_speed_kt=num(f["ground_speed_kt"]), heading_deg=num(f["heading_deg"]), track_deg=num(f["track_deg"]),
        above_ground_altitude_ft=num(f["above_ground_altitude_ft"]), mean_sea_level_altitude_ft=num(f["mean_sea_level_altitude_ft"]),
        callsign=f["callsign"].fillna(""), tail_number=f["tail_number"].fillna(""), adshex=f["adshex"].fillna(""), squawk=f["squawk"].fillna(""),
        ac_type=f["ac_type"].fillna(""), flight_ref=f["flight_ref"].fillna(""),
    ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    a = ap.parse_args()
    case = pathlib.Path(a.case)

    # the append path: one row per emitted plot, event_created_at is when fusion produced it
    f = pd.read_parquet(case / "fusion_append.parquet")
    frame = common_columns(f, "event_created_at_us", "position_timestamp_us")
    frame.insert(0, "track_id", f["tracked_object_id"])
    frame["quality"] = "APPEND_ONLY"
    frame["valid_to_us"] = pd.array([None] * len(frame), dtype="Int64")
    frame["flight_id"] = f["flight_id"].fillna("")
    out = case / "runs" / "prod_fusion_append"; out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out / "fused_plots.parquet", index=False)
    print(f"prod_fusion_append: {len(frame)} fused plots, {frame['track_id'].nunique()} tracks")

    # the final table: created_at and valid_to say when each version of a plot was current
    f = pd.read_parquet(case / "fusion_final.parquet")
    frame = common_columns(f, "created_at_us", "position_timestamp_us")
    frame.insert(0, "track_id", f["track_identifier"])
    frame["quality"] = "REGULAR"
    frame["valid_to_us"] = num(f["valid_to_us"], "Int64")
    frame["flight_id"] = f["flight_plan_id"].fillna("")
    frame["source_track_identifier"] = ""   # the provider table does not keep the source's own track id
    out = case / "runs" / "prod_fusion_regular"; out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out / "fused_plots.parquet", index=False)
    print(f"prod_fusion_regular: {len(frame)} fused plots, {frame['track_id'].nunique()} tracks, {frame['valid_to_us'].notna().sum()} later rewritten")


if __name__ == "__main__":
    main()
