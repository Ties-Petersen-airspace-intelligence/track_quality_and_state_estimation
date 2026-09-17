"""Run BigQuery through the bq command line tool. Always dry run first and show the cost."""
import json, os, subprocess, sys

BQ = "/opt/homebrew/share/google-cloud-sdk/bin/bq"
PRICE_PER_TB = 6.25


def _run(sql: str, dry_run: bool, max_rows: int) -> dict:
    cmd = [BQ, "query", "--use_legacy_sql=false", "--format=json", f"--max_rows={max_rows}"]
    if dry_run:
        cmd.append("--dry_run")
    out = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"bq failed:\n{out.stderr}\n{out.stdout}")
    return json.loads(out.stdout) if out.stdout.strip() else {}


def dry_run_gb(sql: str) -> float:
    r = _run(sql, True, 1)
    st = r.get("statistics", {})
    b = st.get("totalBytesProcessed") or st.get("query", {}).get("totalBytesProcessed")
    return int(b) / 1e9


def report_cost(name: str, sql: str) -> float:
    gb = dry_run_gb(sql)
    print(f"[{name}] dry run: {gb:.1f} GB, about ${gb / 1000 * PRICE_PER_TB:.2f}")
    return gb


def run(name: str, sql: str, max_rows: int = 5_000_000, confirm_above_gb: float = 200) -> list[dict]:
    gb = report_cost(name, sql)
    if gb > confirm_above_gb and not os.environ.get("BQ_YES"):
        ans = input(f"[{name}] more than {confirm_above_gb} GB. Run anyway? [y/N] ")
        if ans.strip().lower() != "y":
            sys.exit("stopped")
    rows = _run(sql, False, max_rows)
    print(f"[{name}] {len(rows)} rows")
    return rows
