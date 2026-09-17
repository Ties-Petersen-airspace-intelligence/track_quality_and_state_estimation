"""Add exact microsecond timestamps to a case pulled with bq.

The bq JSON export rounds TIMESTAMP columns down to whole seconds. BigQuery keeps the
result of every query for 24 hours in an anonymous table, so this reads those tables
(cheap, they are small) and adds one integer column per timestamp column, named
<column>_us, with the exact microseconds.

usage: uv run src/data/cases/add_micros.py --case src/data/cases/<name>/case.json --jobs <name>=<job id> ...
"""
import argparse, json, pathlib, subprocess, sys

import pandas as pd

BQ = "/opt/homebrew/share/google-cloud-sdk/bin/bq"


def bq_json(args: list[str], stdin: str | None = None):
    out = subprocess.run([BQ] + args, input=stdin, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"bq failed ({' '.join(args[:3])}): {out.stderr or out.stdout}")
    return json.loads(out.stdout) if out.stdout.strip() else None


def timestamp_paths(fields: list[dict], prefix: str = "") -> list[str]:
    paths = []
    for f in fields:
        name = prefix + f["name"]
        if f["type"] == "TIMESTAMP":
            paths.append(name)
        elif f["type"] == "RECORD" and f.get("mode") != "REPEATED":
            paths += timestamp_paths(f["fields"], name + ".")
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--jobs", nargs="+", required=True, help="name=jobId pairs")
    a = ap.parse_args()
    folder = pathlib.Path(a.case).parent

    for pair in a.jobs:
        name, job = pair.split("=")
        table = bq_json(["show", "--format=json", "-j", job])["configuration"]["query"]["destinationTable"]
        full = f"{table['projectId']}.{table['datasetId']}.{table['tableId']}"
        schema = bq_json(["show", "--format=json", f"{table['projectId']}:{table['datasetId']}.{table['tableId']}"])["schema"]["fields"]
        paths = timestamp_paths(schema)
        if not paths:
            print(f"{name}: no timestamp columns"); continue

        # one integer column per timestamp column, plus a row number to join on the same order
        extras = ", ".join(f"UNIX_MICROS({p}) AS `{p.replace('.', '_')}_us`" for p in paths)
        sql = f"SELECT {extras} FROM `{full}`"
        st = bq_json(["query", "--use_legacy_sql=false", "--dry_run", "--format=json"], sql)["statistics"]
        gb = int(st.get("totalBytesProcessed") or st["query"]["totalBytesProcessed"]) / 1e9
        rows = bq_json(["query", "--use_legacy_sql=false", "--format=json", "--max_rows=5000000"], sql) or []

        frame = pd.read_parquet(folder / f"{name}.parquet")
        if len(rows) != len(frame):
            sys.exit(f"{name}: {len(rows)} rows from BigQuery but {len(frame)} in the parquet file, order cannot be trusted")
        # the anonymous table keeps the rows in query output order, same as the JSON export we converted
        micros = pd.DataFrame(rows)
        for col in micros.columns:
            frame[col] = pd.to_numeric(micros[col]).astype("Int64")
        frame.to_parquet(folder / f"{name}.parquet", index=False)
        print(f"{name}: {len(paths)} timestamp columns made exact ({gb:.3f} GB scanned)")


if __name__ == "__main__":
    main()
