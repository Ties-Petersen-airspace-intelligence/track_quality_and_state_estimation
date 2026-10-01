"""Add Aireon plots to a case, from the raw Aireon backup in S3 (AWS dev).

usage: uv run data/cases/add_aireon.py --case data/cases/<name>/case.json --backup <folder>

Aireon (space-based ADS-B, source 13) runs only in dev, and its plots are not in BigQuery. The backup keeps what
uni-aireon-integration published to Pulsar: one CSV line of ASTERIX CAT021 fields per plot, in Parquet files per hour.
Download the hours of the case first, for example:

  aws --profile dev s3 cp --recursive \\
    s3://uni-aireon-integration-raw-use2-dev/uni-pubsub-backup/integrations/uni-aireon-integration/stream-raw/date=2026-09-30/hour=05/ \\
    <folder>/date=2026-09-30/hour=05/

This turns each line into the plot uni-track-source-aireon-stream-global makes (src/aireon/converter.rs, commit caa37c0),
as BigQuery-style columns, so raw_plots.py reads it like every other source. Kept: the plots in the box and window of
case.json, plus the aircraft's hex anywhere, as in pull_flight_case.py. Dropped: plots without a hex, since production
keeps them off the topic the multiplexer reads. Two choices of our own:
- asi_received_timestamp is the time the line was published to Pulsar; production uses the moment it converts the line,
  right after
- duplicates stay, since production gets them too
Writes raw/aireon.parquet next to case.json. Run from src/.
"""
import argparse, datetime, json, pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

COLUMNS = ["target_address", "target_identification", "mode_3a_code", "timestamp", "ground_bit", "latitude", "longitude",
           "flight_level", "geometric_altitude_ft", "barometric_vertical_rate", "geometric_vertical_rate",
           "ground_speed_nm_per_sec", "track_angle_deg", "position_quality", "surface_north_code", "surface_ground_speed_kt",
           "surface_track_angle_deg"]
QUALITY = {0: "POSITION_QUALITY_LOW", 1: "POSITION_QUALITY_MEDIUM", 2: "POSITION_QUALITY_HIGH"}
NORTH = {0: "GROUND_TRACK_REFERENCE_TRUE_NORTH", 1: "GROUND_TRACK_REFERENCE_MAGNETIC_NORTH"}


def hour_folders(backup: pathlib.Path, case: dict) -> list[pathlib.Path]:
    """The hour folders that can hold the window; a line is published a few minutes after its position time."""
    start = datetime.datetime.fromisoformat(case["t_start"])
    end = datetime.datetime.fromisoformat(case["t_end"]) + datetime.timedelta(minutes=30)
    folders, hour = [], start.replace(minute=0, second=0)
    while hour < end:
        folder = backup / f"date={hour:%Y-%m-%d}" / f"hour={hour:%H}"
        if not folder.exists():
            raise SystemExit(f"missing {folder}, download it first (see the docstring)")
        folders.append(folder)
        hour += datetime.timedelta(hours=1)
    return folders


def read_lines(folder: pathlib.Path) -> pd.DataFrame:
    """Every CSV line of one hour, split into its 17 columns, with the publish time."""
    parts = []
    for path in sorted(folder.glob("*.parquet")):
        frame = pq.read_table(path, columns=["publish_time", "payload"]).to_pandas()
        lines = frame["payload"].map(lambda b: b.decode("ascii", "replace"))
        fields = lines.str.split(",", expand=True)
        fields = fields[fields.columns[:len(COLUMNS)]] if fields.shape[1] >= len(COLUMNS) else None
        if fields is None:
            continue
        fields.columns = COLUMNS
        fields = fields.apply(lambda column: column.str.strip())
        fields["publish_time"] = frame["publish_time"]
        parts.append(fields[lines.str.count(",") == len(COLUMNS) - 1])   # the converter refuses other column counts
    return pd.concat(parts, ignore_index=True)


def in_case(lines: pd.DataFrame, case: dict) -> pd.DataFrame:
    """Plots in the window, inside the box or with the aircraft's hex, as pull_flight_case.py selects them."""
    b = case["box"]
    latitude, longitude = pd.to_numeric(lines["latitude"], errors="coerce"), pd.to_numeric(lines["longitude"], errors="coerce")
    in_window = (lines["timestamp"] >= case["t_start"]) & (lines["timestamp"] < case["t_end"])
    in_box = latitude.between(b["lat_min"], b["lat_max"]) & longitude.between(b["lon_min"], b["lon_max"])
    own = lines["target_address"].str.upper() == case["hex"].upper()
    return lines[in_window & (in_box | own) & (lines["target_address"] != "")]


def micros(column: pd.Series) -> np.ndarray:
    """UTC time to epoch microseconds, whatever resolution pandas parsed it in."""
    return pd.to_datetime(column, utc=True).dt.as_unit("us").astype("int64").to_numpy()


def number(column: pd.Series) -> pd.Series:
    return pd.to_numeric(column.replace("", np.nan), errors="coerce")


def to_plots(lines: pd.DataFrame) -> pd.DataFrame:
    """The converter's mapping, field by field (converter.rs lines 11 to 112)."""
    f32 = lambda s: number(s).astype("float32")
    flight_level, geometric = f32(lines["flight_level"]), f32(lines["geometric_altitude_ft"])
    barometric_ft = (flight_level * np.float32(100)).apply(lambda v: np.nan if np.isnan(v) else float(int(v)))
    geometric_ft = geometric.apply(lambda v: np.nan if np.isnan(v) else float(int(v)))
    speed = (f32(lines["ground_speed_nm_per_sec"]) * np.float32(3600)).fillna(f32(lines["surface_ground_speed_kt"]))
    position_us = micros(lines["timestamp"])
    ground, quality, north = number(lines["ground_bit"]), number(lines["position_quality"]), number(lines["surface_north_code"])
    return pd.DataFrame({
        "common.longitude": f32(lines["longitude"]).to_numpy(),
        "common.latitude": f32(lines["latitude"]).to_numpy(),
        "common.position_timestamp": position_us,
        "common.source_received_timestamp": position_us,
        "common.asi_received_timestamp": micros(lines["publish_time"]),
        "common.source_identifier": "AIREON_STREAM_GLOBAL",
        "common.track_identifier": lines["target_address"].to_numpy(),
        "common.adshex": lines["target_address"].to_numpy(),
        "common.callsign": lines["target_identification"].to_numpy(),
        "common.squawk": lines["mode_3a_code"].to_numpy(),
        "common.altitude_ft": barometric_ft.fillna(geometric_ft).to_numpy(),   # barometric first, else geometric
        "common.ground_speed_kt": speed.to_numpy(),
        "common.track_deg": f32(lines["track_angle_deg"]).fillna(f32(lines["surface_track_angle_deg"])).to_numpy(),
        "is_on_ground": ground.map({0: False, 1: True}).to_numpy(),
        "barometric_altitude_ft": barometric_ft.to_numpy(),
        "geometric_altitude_ft": geometric_ft.to_numpy(),
        "barometric_vertical_rate_ft_per_min": f32(lines["barometric_vertical_rate"]).to_numpy(),
        "geometric_vertical_rate_ft_per_min": f32(lines["geometric_vertical_rate"]).to_numpy(),
        "position_quality": quality.map(QUALITY).fillna("POSITION_QUALITY_UNSPECIFIED").to_numpy(),
        "surface_track_reference": north.map(NORTH).fillna("GROUND_TRACK_REFERENCE_UNSPECIFIED").to_numpy(),
        "surface_ground_speed_kt": f32(lines["surface_ground_speed_kt"]).to_numpy(),
        "surface_track_angle_deg": f32(lines["surface_track_angle_deg"]).to_numpy(),
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--backup", required=True, help="local copy of the stream-raw backup, with date=/hour= folders")
    args = parser.parse_args()
    case_file = pathlib.Path(args.case)
    case = json.loads(case_file.read_text())
    if case["env"] != "dev":
        raise SystemExit("Aireon runs only in dev; a prod case keeps only what prod had")

    # the lines of the case, hour by hour
    kept = [in_case(read_lines(folder), case) for folder in hour_folders(pathlib.Path(args.backup), case)]
    lines = pd.concat(kept, ignore_index=True)

    # converted like production, in the order we received them
    plots = to_plots(lines).sort_values(["common.asi_received_timestamp", "common.position_timestamp"], kind="stable")
    plots.to_parquet(case_file.parent / "raw" / "aireon.parquet", index=False)

    case.setdefault("rows", {})["aireon"] = len(plots)
    case_file.write_text(json.dumps(case, indent=1) + "\n")
    print(f"aireon {len(plots):9d} rows, {int((plots['common.adshex'].str.upper() == case['hex'].upper()).sum())} of {case['hex']}")


if __name__ == "__main__":
    main()
