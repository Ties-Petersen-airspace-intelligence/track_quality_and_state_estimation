"""Pull a case for one aircraft from a bug ticket: every plot in the box and window, plus the aircraft's own plots anywhere.

usage: uv run data/cases/pull_flight_case.py --case data/cases/<name>/case.json [--dry-run] [--raw-from data/cases/<other case>]

A flight that crosses a continent does not fit one box, and a wrong plot can sit far from the aircraft,
so next to the box this also takes every plot with the aircraft's hex. Production fusion comes from the
environment the ticket was seen in, prod or dev, and can be read as it was at an earlier time (BigQuery
time travel, at most 7 days back), for append partitions that have expired since.

case.json holds, before the pull: name, day, t_start, t_end, box, hex, env ("prod" or "dev"),
optionally as_of ("YYYY-MM-DD HH:MM:SS", UTC, for the fusion tables), suspect, ticket, reason.
--raw-from copies raw/ from a case with the same day, window, box and hex, so a prod and a dev
case of one ticket pay for the raw plots once.
Writes raw/, production/ and sql/ next to case.json, like pull_case.py, with exact microseconds in <column>_us.
Run from src/.
"""
import argparse, json, pathlib, shutil, sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from add_micros import timestamp_paths
from pull_case import PRICE_PER_TB, TABLES, dry_run_gb, table_path
from pull_cases import as_strings, bq, query_to_table, read_pages

RAW = [name for name in TABLES if not name.startswith("fusion_")]
FUSION = {
    "prod": {"fusion_append": "flyways-aws-prod.uni_track_fusion.append_only_plots", "fusion_final": "flyways.uni_track_provider.fused_plots_aws"},
    "dev": {"fusion_append": "flyways-aws-dev.uni_track_fusion.append_only_plots", "fusion_final": "flyways-dev.uni_track_provider.fused_plots_aws"},
}
SAME_RAW = ["day", "t_start", "t_end", "box", "hex"]


def table_for(name: str, case: dict) -> str:
    return FUSION[case["env"]][name] if name in FUSION[case["env"]] else TABLES[name][0]


def with_micros(table: str) -> str:
    """t.* plus exact microseconds per timestamp column, since bq JSON rounds timestamps to seconds."""
    project, rest = table.split(".", 1)
    schema = json.loads(bq("show", "--format=json", f"{project}:{rest}"))["schema"]["fields"]
    return "t.*" + "".join(f", UNIX_MICROS(t.{p}) AS `{p.replace('.', '_')}_us`" for p in timestamp_paths(schema))


def sql_for(name: str, case: dict, select: str) -> str:
    """Plots of one table in the window: inside the box, or with the aircraft's hex anywhere."""
    _, part, lat, lon, ts = TABLES[name]
    hex_column = "adshex" if name.startswith("fusion_") else "common.adshex"
    as_of = f" FOR SYSTEM_TIME AS OF TIMESTAMP('{case['as_of']}+00')" if name.startswith("fusion_") and case.get("as_of") else ""
    b = case["box"]
    return (f"SELECT {select} FROM `{table_for(name, case)}` AS t{as_of} WHERE DATE(t.{part}) = '{case['day']}' "
            f"AND t.{ts} >= TIMESTAMP('{case['t_start']}') AND t.{ts} < TIMESTAMP('{case['t_end']}') "
            f"AND ((t.{lat} BETWEEN {b['lat_min']} AND {b['lat_max']} AND t.{lon} BETWEEN {b['lon_min']} AND {b['lon_max']}) "
            f"OR UPPER(t.{hex_column}) = '{case['hex'].upper()}')")


def copy_raw(source: pathlib.Path, folder: pathlib.Path, case: dict) -> dict:
    """Raw tables of a sibling case pulled for the same window, box and hex."""
    other = json.loads((source / "case.json").read_text())
    if any(other[key] != case[key] for key in SAME_RAW):
        sys.exit(f"{source.name} has another {', '.join(k for k in SAME_RAW if other[k] != case[k])}, its raw plots do not fit")
    for name in RAW:
        shutil.copy(table_path(source, name), table_path(folder, name))
        shutil.copy(source / "sql" / f"{name}.sql", folder / "sql" / f"{name}.sql")
    # Aireon plots come from add_aireon.py, not from BigQuery, and only dev has Aireon
    if case["env"] == "dev" and (source / "raw" / "aireon.parquet").exists():
        shutil.copy(source / "raw" / "aireon.parquet", folder / "raw" / "aireon.parquet")
    copied = RAW + ["aireon"] if case["env"] == "dev" else RAW
    return {name: other["rows"][name] for name in copied if name in other["rows"]}


def pull(name: str, case: dict, folder: pathlib.Path) -> int:
    """Run once, read the saved result page by page, write one Parquet file."""
    table, total = query_to_table(sql_for(name, case, with_micros(table_for(name, case))))
    parts = [as_strings(frame) for frame in read_pages(table, total) if len(frame)]
    if parts:
        pq.write_table(pa.concat_tables(parts, promote_options="default"), table_path(folder, name))
    else:
        pd.DataFrame().to_parquet(table_path(folder, name), index=False)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--raw-from", help="case folder whose raw/ to copy instead of querying")
    args = parser.parse_args()
    case_file = pathlib.Path(args.case)
    case = json.loads(case_file.read_text())
    folder = case_file.parent
    names = [n for n in TABLES if n.startswith("fusion_")] if args.raw_from else list(TABLES)

    # cost first
    total = 0.0
    for name in names:
        gigabytes = dry_run_gb(sql_for(name, case, "t.*"))
        total += gigabytes
        print(f"{name:14s} {table_for(name, case):60s} {gigabytes:8.1f} GB  ${gigabytes / 1000 * PRICE_PER_TB:.2f}")
    print(f"{'total':14s} {'':60s} {total:8.1f} GB  ${total / 1000 * PRICE_PER_TB:.2f}")
    if args.dry_run:
        return

    # then the data
    (folder / "sql").mkdir(exist_ok=True)
    counts = copy_raw(pathlib.Path(args.raw_from), folder, case) if args.raw_from else {}
    for name in names:
        counts[name] = pull(name, case, folder)
        (folder / "sql" / f"{name}.sql").write_text(sql_for(name, case, "t.*") + "\n")
        print(f"{name:14s} {counts[name]:9d} rows", flush=True)
    case["rows"] = counts
    case_file.write_text(json.dumps(case, indent=1) + "\n")


if __name__ == "__main__":
    main()
