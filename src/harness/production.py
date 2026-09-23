"""Turn the production fusion tables of a case into runs, so the viewer can replay them like a strategy.

usage: uv run -m harness.production --case data/cases/<name>      # or a folder of cases

Each command makes two runs, runs/prod_fusion_append/<label> and runs/prod_fusion_regular/<label>, with a
run.json like any strategy run (see runs.py).
runs/prod_fusion_append: what production's append path first emitted (append_only_plots). Rows are never
invalidated, the table has no such column, so every plot stays.
runs/prod_fusion_regular: production's result after the regular and recorrelation rewrites, from the provider
table (fused_plots_aws), with created_at and valid_to as
BigQuery holds them, so rewrites replace the past exactly as consumers saw it.
"""
from __future__ import annotations

import argparse, pathlib, time

import pandas as pd

from . import runs

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
    ap.add_argument("--case", required=True, nargs="+", help="case folder(s), or a folder that holds case folders")
    ap.add_argument("--note", default="", help="free text stored with the runs")
    a = ap.parse_args()
    batch, git = runs.new_batch(), runs.git_info()
    for case in runs.case_folders(a.case):
        convert(case, a.note, batch, git)


def convert(case: pathlib.Path, note: str, batch: str, git: dict) -> None:
    label = runs.next_label(case, "prod_fusion")   # one label for both production runs of a case

    # the append path: one row per emitted plot, event_created_at is when fusion produced it
    started = time.time()
    f = pd.read_parquet(case / "fusion_append.parquet")
    frame = common_columns(f, "event_created_at_us", "position_timestamp_us")
    frame.insert(0, "track_id", f["tracked_object_id"])
    frame["quality"] = "APPEND_ONLY"
    frame["valid_to_us"] = pd.array([None] * len(frame), dtype="Int64")
    frame["flight_id"] = f["flight_id"].fillna("")
    store(case, "prod_fusion_append", frame, note or "production append path, from flyways-aws-prod.uni_track_fusion.append_only_plots", batch, git, started, label)

    # the final table: created_at and valid_to say when each version of a plot was current
    started = time.time()
    f = pd.read_parquet(case / "fusion_final.parquet")
    frame = common_columns(f, "created_at_us", "position_timestamp_us")
    frame.insert(0, "track_id", f["track_identifier"])
    frame["quality"] = "REGULAR"
    frame["valid_to_us"] = num(f["valid_to_us"], "Int64")
    frame["flight_id"] = f["flight_plan_id"].fillna("")
    frame["source_track_identifier"] = ""   # the provider table does not keep the source's own track id
    store(case, "prod_fusion_regular", frame, note or "production after regular and recorrelation rewrites, from flyways.uni_track_provider.fused_plots_aws", batch, git, started, label)


def store(case: pathlib.Path, name: str, frame: pd.DataFrame, note: str, batch: str, git: dict, started: float, label: str) -> None:
    out = runs.new_run(case, name, label)
    frame.to_parquet(out / "fused_plots.parquet", index=False)
    counts = dict(fused_plots=len(frame), tracks=int(frame["track_id"].nunique()), rewritten=int(frame["valid_to_us"].notna().sum()))
    runs.write_manifest(out, name, label, batch, case, params={}, note=note, counts=counts, duration_s=time.time() - started, git=git)
    print(f"{case.name} {name}/{label}: {len(frame)} fused plots, {counts['tracks']} tracks, {counts['rewritten']} later rewritten")


if __name__ == "__main__":
    main()
