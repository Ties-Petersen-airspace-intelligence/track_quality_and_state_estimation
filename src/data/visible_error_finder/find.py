"""Step 1: find steps in fused tracks that look wrong, for one day and both fusion tables.

usage: uv run data/visible_error_finder/find.py --day 2026-09-22 [--dry-run] [--saved append=<table>]

--saved reads the result table of an earlier run of the steps query (BigQuery keeps
it for 24 hours) instead of scanning the fusion table again.

Writes out/<day>/events_<table>.parquet. Run from src/.
"""
import argparse, pathlib

import bq

HERE = pathlib.Path(__file__).parent
TABLES = {
    "append": ("flyways-aws-prod.uni_track_fusion.append_only_plots", "TRUE"),
    "regular": ("flyways.uni_track_provider.fused_plots_aws", "valid_to IS NULL"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--saved", action="append", default=[], help="name=table of an earlier steps result")
    args = parser.parse_args()
    saved = dict(item.split("=", 1) for item in args.saved)
    out = HERE / "out" / args.day
    out.mkdir(parents=True, exist_ok=True)
    steps_template = (HERE / "sql" / "steps.sql").read_text()
    keep_template = (HERE / "sql" / "keep.sql").read_text()

    for name, (table, current) in TABLES.items():
        steps = f"SELECT * FROM `{saved[name]}`" if name in saved else steps_template.format(table=table, day=args.day, current=current)
        sql = keep_template.replace("{events}", steps)
        (out / f"steps_{name}.sql").write_text(sql)

        # cost first
        gigabytes, dollars = bq.cost(sql)
        print(f"{name} {args.day}: {gigabytes:.1f} GB, ${dollars:.2f}")
        if args.dry_run:
            continue

        events = bq.run(sql)
        events.to_parquet(out / f"events_{name}.parquet")
        print(f"  {len(events)} events on {events.tid.nunique()} tracks")
        print("  " + events.kind_group.value_counts().to_string().replace("\n", "\n  "))


if __name__ == "__main__":
    main()
