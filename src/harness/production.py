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

RAW_SOURCES = {4: "adsbx", 3: "planefinder", 11: "uavionix", 10: "stdds", 1: "tfms_ti", 2: "tfms_or", 6: "ual", 5: "asa"}

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


def raw_outcomes(case: pathlib.Path, fused: pd.DataFrame) -> pd.DataFrame:
    """Production copies a raw plot into a fused plot, so a raw plot was used when a fused plot from the same
    source has the same position time to the microsecond. Production does not say why it left a plot out,
    so every other plot is "unknown"."""
    rows = []
    for source_id, name in RAW_SOURCES.items():
        path = case / f"{name}.parquet"
        if not path.exists():
            continue
        raw = pd.read_parquet(path)
        if raw.empty:
            continue
        col = "common_position_timestamp_us" if "common_position_timestamp_us" in raw.columns else "common.position_timestamp"
        position_us = pd.to_numeric(raw[col], errors="coerce").astype("Int64")
        taken = fused[fused["source_identifier"] == source_id].drop_duplicates("position_us").set_index("position_us")["track_id"]
        track = position_us.map(taken)
        rows.append(pd.DataFrame(dict(source=name, position_us=position_us, source_track_identifier=raw["common.track_identifier"].fillna(""),
                                      state=track.notna().map({True: "used", False: "unknown"}), track_id=track.astype("string"), reason="")))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["source", "position_us", "source_track_identifier", "state", "track_id", "reason"])


def store(case: pathlib.Path, name: str, frame: pd.DataFrame, note: str, batch: str, git: dict, started: float, label: str) -> None:
    out = runs.new_run(case, name, label)
    frame.to_parquet(out / "fused_plots.parquet", index=False)
    outcomes = raw_outcomes(case, frame)
    outcomes.to_parquet(out / "raw_outcomes.parquet", index=False)
    counts = dict(raw_plots=len(outcomes), fused_plots=len(frame), tracks=int(frame["track_id"].nunique()), rewritten=int(frame["valid_to_us"].notna().sum()),
                  outcomes=outcomes["state"].value_counts().to_dict(), reasons={})
    runs.write_manifest(out, name, label, batch, case, params={}, note=note, counts=counts, duration_s=time.time() - started, git=git)
    print(f"{case.name} {name}/{label}: {len(frame)} fused plots, {counts['tracks']} tracks, {counts['rewritten']} later rewritten")


if __name__ == "__main__":
    main()
