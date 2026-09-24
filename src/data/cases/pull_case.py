"""Pull the raw plots of every source, plus the current fusion output, for one case box and time window.

usage: uv run src/data/cases/pull_case.py --case src/data/cases/<name>/case.json [--dry-run] [--from-json DIR]

Reads box, day and window from case.json, dry runs every query and prints the cost,
then writes one Parquet file per source next to case.json. --from-json converts bq JSON
files that were already downloaded instead of querying again.
"""
import argparse, json, pathlib, subprocess, sys

import pandas as pd

BQ = "/opt/homebrew/share/google-cloud-sdk/bin/bq"
PRICE_PER_TB = 6.25

# name: table, partition column, latitude, longitude, position time column
TABLES = {
    "adsbx": ("uni-adsbx-integration-master.adsbx_integration.adsbx_positions", "position_timestamp", "common.latitude", "common.longitude", "common.position_timestamp"),
    "planefinder": ("flyways.planefinder_positions.planefinder_positions", "pos_update_time", "common.latitude", "common.longitude", "common.position_timestamp"),
    "uavionix": ("flyways-aws-prod.uni_track_source_uavionix.uni_track_source_uavionix_flightline_asterix_cat021", "position_timestamp", "common.latitude", "common.longitude", "position_timestamp"),
    "stdds": ("flyways-aws-prod.uni_track_source_stdds.uni_track_source_stdds_position_reports", "position_timestamp", "common.latitude", "common.longitude", "position_timestamp"),
    "tfms_ti": ("flyways.tfms_ti_positions.tfms_ti_positions", "position_timestamp", "common.latitude", "common.longitude", "common.position_timestamp"),
    "tfms_or": ("flyways.tfms_or_positions.tfms_or_positions", "position_timestamp", "common.latitude", "common.longitude", "common.position_timestamp"),
    "ual": ("flyways.ual_integration.ual_positions", "source_timestamp", "common.latitude", "common.longitude", "common.position_timestamp"),
    "asa": ("flyways.asa_positions.asa_positions", "position_timestamp", "common.latitude", "common.longitude", "common.position_timestamp"),
    "fusion_append": ("flyways-aws-prod.uni_track_fusion.append_only_plots", "position_timestamp", "latitude", "longitude", "position_timestamp"),
    "fusion_final": ("flyways.uni_track_provider.fused_plots_aws", "position_timestamp", "latitude", "longitude", "position_timestamp"),
}


def sql_for(name: str, case: dict) -> str:
    table, part, lat, lon, ts = TABLES[name]
    b = case["box"]
    return (f"SELECT * FROM `{table}` WHERE DATE({part}) = '{case['day']}' "
            f"AND {ts} >= TIMESTAMP('{case['t_start']}') AND {ts} < TIMESTAMP('{case['t_end']}') "
            f"AND {lat} BETWEEN {b['lat_min']} AND {b['lat_max']} AND {lon} BETWEEN {b['lon_min']} AND {b['lon_max']}")


def run_bq(sql: str, dry_run: bool) -> str:
    cmd = [BQ, "query", "--use_legacy_sql=false", "--format=json", "--max_rows=5000000"] + (["--dry_run"] if dry_run else [])
    out = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"bq failed:\n{out.stderr}")
    return out.stdout


def dry_run_gb(sql: str) -> float:
    st = json.loads(run_bq(sql, True)).get("statistics", {})
    return int(st.get("totalBytesProcessed") or st["query"]["totalBytesProcessed"]) / 1e9


def table_path(folder: pathlib.Path, name: str) -> pathlib.Path:
    """Where a pulled table lives in a case folder: raw/<source>.parquet, production/append.parquet, production/final.parquet."""
    path = folder / "production" / f"{name.removeprefix('fusion_')}.parquet" if name.startswith("fusion_") else folder / "raw" / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def to_parquet(rows: list[dict], path: pathlib.Path) -> int:
    # bq JSON gives every scalar as a string; keep them as strings here, the loader in the harness types the columns it uses
    frame = pd.json_normalize(rows, sep=".") if rows else pd.DataFrame()
    frame.to_parquet(path, index=False)
    return len(frame)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-json", help="folder with <name>.json files already downloaded with bq")
    a = ap.parse_args()
    case_file = pathlib.Path(a.case)
    case = json.loads(case_file.read_text())
    folder = case_file.parent

    # cost first
    total = 0.0
    for name in TABLES:
        gb = dry_run_gb(sql_for(name, case))
        total += gb
        print(f"{name:14s} {gb:8.1f} GB  ${gb / 1000 * PRICE_PER_TB:.2f}")
    print(f"{'total':14s} {total:8.1f} GB  ${total / 1000 * PRICE_PER_TB:.2f}")
    if a.dry_run:
        return

    # then the data
    counts = {}
    for name in TABLES:
        if a.from_json:
            text = (pathlib.Path(a.from_json) / f"{name}.json").read_text()
        else:
            text = run_bq(sql_for(name, case), False)
        rows = json.loads(text) if text.strip() else []
        counts[name] = to_parquet(rows, table_path(folder, name))
        print(f"{name:14s} {counts[name]:8d} rows")
    (folder / "sql").mkdir(exist_ok=True)
    for name in TABLES:
        (folder / "sql" / f"{name}.sql").write_text(sql_for(name, case) + "\n")
    case["rows"] = counts
    case_file.write_text(json.dumps(case, indent=1) + "\n")


if __name__ == "__main__":
    main()
