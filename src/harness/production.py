"""Production's output for a case, in the same shape as a strategy run, so the viewer can replay it like one.

Nothing is stored: the viewer server calls load() on the two tables pulled with the case.
prod_fusion_append: production/append.parquet, what production's append path first emitted (append_only_plots).
    Rows are never invalidated, the table has no such column, so every plot stays.
prod_fusion_regular: production/final.parquet, production's result after the regular and recorrelation rewrites,
    from the provider table (fused_plots_aws), with created_at and valid_to as BigQuery holds them, so rewrites
    replace the past exactly as consumers saw it.
"""
from __future__ import annotations

import pathlib

import pandas as pd

PARTS = {"prod_fusion_append": "append", "prod_fusion_regular": "final"}
RAW_SOURCES = {4: "adsbx", 3: "planefinder", 11: "uavionix", 10: "stdds", 1: "tfms_ti", 2: "tfms_or", 6: "ual", 5: "asa"}
TIMESTAMPS = ["position_timestamp", "source_received_timestamp", "asi_received_timestamp"]
NUMBERS = ["source_identifier", "latitude", "longitude", "altitude_ft", "ground_speed_kt", "heading_deg", "track_deg", "above_ground_altitude_ft",
           "mean_sea_level_altitude_ft", "selected_altitude_ft", "vert_rate_fpm", "pressure_hpa"]
TEXTS = ["callsign", "tail_number", "adshex", "squawk", "ac_type", "flight_number", "flight_ref", "original_callsign", "origin", "destination"]


def load(case: pathlib.Path, name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The fused plots and the raw plot outcomes of prod_fusion_append or prod_fusion_regular."""
    part = PARTS[name]
    f = pd.read_parquet(case / "production" / f"{part}.parquet")
    micros = lambda column: pd.to_numeric(f[column + "_us"], errors="coerce").astype("Int64")

    # the event fields: the append table knows the event time, the final table when each version was current
    if part == "append":
        fused = pd.DataFrame(dict(track_id=f["tracked_object_id"], created_at=micros("event_created_at"), quality="APPEND_ONLY", valid_to=pd.array([None] * len(f), dtype="Int64"),
                                  track_identifier=f["track_identifier"].fillna(""), flight_id=f["flight_id"].fillna("")))
    else:
        # the provider table keeps the fused track id in track_identifier and not the source's own track id
        fused = pd.DataFrame(dict(track_id=f["track_identifier"], created_at=micros("created_at"), quality="REGULAR", valid_to=micros("valid_to"),
                                  track_identifier="", flight_id=f["flight_plan_id"].fillna("")))

    # the plot fields under their proto names, where the table has them
    for column in TIMESTAMPS:
        fused[column] = micros(column)
    for column in NUMBERS:
        if column in f.columns:
            fused[column] = pd.to_numeric(f[column], errors="coerce")
    for column in TEXTS:
        if column in f.columns:
            fused[column] = f[column].fillna("")
    fused["since"] = fused["until"] = fused["position_timestamp"]
    # the append table keeps the source's own track id; the final table only the hex
    return fused, raw_outcomes(case, fused, "track_identifier" if part == "append" else "adshex")


def raw_outcomes(case: pathlib.Path, fused: pd.DataFrame, identity: str) -> pd.DataFrame:
    """Production copies a raw plot into a fused plot, so a raw plot was used when a fused plot from the same
    source has the same position time to the microsecond and the same identity: the source track id, or the hex
    where the table has no source track id. Raw plots that are exact duplicates all count as used. Production does
    not say why it left a plot out, so every other plot is unknown."""
    parts = []
    for source_id, source in RAW_SOURCES.items():
        path = case / "raw" / f"{source}.parquet"
        if not path.exists():
            continue
        raw = pd.read_parquet(path)
        if raw.empty:
            continue
        column = "common_position_timestamp_us" if "common_position_timestamp_us" in raw.columns else "common.position_timestamp"
        raw_identity = raw["common.track_identifier" if identity == "track_identifier" else "common.adshex"].fillna("").astype(str)
        keys = pd.MultiIndex.from_arrays([pd.to_numeric(raw[column], errors="coerce").astype("Int64"), raw_identity])
        taken = fused[fused["source_identifier"] == source_id].drop_duplicates(["position_timestamp", identity]).set_index(["position_timestamp", identity])["track_id"]
        track = pd.Series(taken.reindex(keys).to_numpy(), index=raw.index)
        parts.append(pd.DataFrame(dict(source=source, row=range(len(raw)), state=track.notna().map({True: "used", False: "unknown"}), track_id=track.astype("string"), reason="")))
    return pd.concat(parts, ignore_index=True)

