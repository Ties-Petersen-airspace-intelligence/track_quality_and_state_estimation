"""Read-only BigQuery through the bq command line tool: dry run first, then run and save as CSV."""
import io, json, subprocess, sys

import pandas as pd

BQ = "/opt/homebrew/share/google-cloud-sdk/bin/bq"
DOLLARS_PER_TB = 6.25


def cost(sql: str) -> tuple[float, float]:
    """Gigabytes and dollars a query would read, without running it."""
    out = subprocess.run([BQ, "query", "--use_legacy_sql=false", "--dry_run", "--format=json"],
                         input=sql, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"dry run failed:\n{out.stderr}{out.stdout}")
    stats = json.loads(out.stdout)["statistics"]
    gigabytes = int(stats["totalBytesProcessed"]) / 1e9
    return gigabytes, gigabytes / 1000 * DOLLARS_PER_TB


def run(sql: str) -> pd.DataFrame:
    out = subprocess.run([BQ, "query", "--use_legacy_sql=false", "--format=csv", "--max_rows=10000000"],
                         input=sql, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"query failed:\n{out.stderr}{out.stdout}")
    # bq prints nothing at all for an empty result
    return pd.read_csv(io.StringIO(out.stdout)) if out.stdout.strip() else pd.DataFrame()
