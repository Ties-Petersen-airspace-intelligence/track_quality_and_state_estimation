"""Pull many cases at once: one query per source and day for every case of that day.

usage: uv run data/cases/pull_cases.py --cases data/visible_error_finder/out/fw_cases.json [--dry-run] [--count] [--only fw01 fw02]

A case costs a full day scan of every source whatever its box, so cases of the same day share
one scan per source (about $4 per day instead of $4 per case). The cases file is a list with, per
case: name, day, t_event (unix seconds) and regular_track (fused track id). Each case gets the hour
centred on t_event and a box around its regular fusion track in that hour, plus a margin.
Writes src/data/cases/<name>/ like pull_case.py: case.json, one Parquet per source, sql/.
Run from src/.
"""
import argparse, json, pathlib, subprocess, sys, time, uuid
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from add_micros import timestamp_paths
from pull_case import BQ, PRICE_PER_TB, TABLES, dry_run_gb, run_bq

HERE = pathlib.Path(__file__).parent
MARGIN_DEG = 0.5            # box margin around the track
HALF_WINDOW = pd.Timedelta(minutes=30)
FUSED = "flyways.uni_track_provider.fused_plots_aws"
PAGE_ROWS = 50_000          # rows per download page, keeps memory small
READERS = 6                 # pages read at the same time


def bq(*args: str, sql: str | None = None) -> str:
    out = subprocess.run([BQ, *args], input=sql, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"bq failed:\n{out.stderr}{out.stdout}")
    return out.stdout


def with_micros(name: str) -> str:
    """t.* plus exact microseconds per timestamp column, since bq JSON rounds timestamps to seconds (as add_micros.py)."""
    table = TABLES[name][0]
    project, rest = table.split(".", 1)
    schema = json.loads(bq("show", "--format=json", f"{project}:{rest}"))["schema"]["fields"]
    extras = "".join(f", UNIX_MICROS(t.{p}) AS `{p.replace('.', '_')}_us`" for p in timestamp_paths(schema))
    return f"c.case_name, t.*{extras}"


def query_to_table(sql: str) -> tuple[str, int]:
    """Run once (billed once) and return the table BigQuery keeps the result in for 24 hours."""
    job_id = f"pull_cases_{uuid.uuid4().hex[:12]}"
    bq("query", "--use_legacy_sql=false", "--format=none", f"--job_id={job_id}", sql=sql)
    job = json.loads(bq("show", "--format=json", "-j", job_id))
    table = job["configuration"]["query"]["destinationTable"]
    info = json.loads(bq("show", "--format=json", f"{table['projectId']}:{table['datasetId']}.{table['tableId']}"))
    return f"{table['projectId']}:{table['datasetId']}.{table['tableId']}", int(info["numRows"])


def read_page(table: str, start: int) -> pd.DataFrame:
    rows = json.loads(bq("head", "--format=json", "-n", str(PAGE_ROWS), "-s", str(start), table) or "[]")
    return pd.json_normalize(rows, sep=".") if rows else pd.DataFrame()


def read_pages(table: str, total: int):
    """The saved result, a few pages at a time so memory stays small; reading it is free."""
    starts = list(range(0, total, PAGE_ROWS))
    with ThreadPoolExecutor(READERS) as pool:
        for group in range(0, len(starts), READERS):
            yield from pool.map(lambda start: read_page(table, start), starts[group:group + READERS])


def as_strings(frame: pd.DataFrame) -> pa.Table:
    """Arrow text columns take far less memory than pandas objects; bq JSON gives strings anyway."""
    return pa.Table.from_pandas(frame.astype("string"), preserve_index=False)


def windows(cases: list[dict]) -> None:
    """The hour centred on the event, as the text case.json uses."""
    for case in cases:
        event = pd.Timestamp(case["t_event"], unit="s")
        start, end = (event - HALF_WINDOW).floor("s"), (event + HALF_WINDOW).floor("s")
        if start.date() != end.date():
            sys.exit(f"{case['name']} crosses midnight, pull it on its own")
        case["t_start"], case["t_end"] = f"{start:%Y-%m-%d %H:%M:%S}", f"{end:%Y-%m-%d %H:%M:%S}"


def extents_sql(cases: list[dict]) -> str:
    rows = ",\n    ".join(f"STRUCT('{c['name']}' AS name, '{c['regular_track']}' AS tid, TIMESTAMP('{c['t_start']}') AS t0, "
                           f"TIMESTAMP('{c['t_end']}') AS t1)" for c in cases)
    days = ", ".join(sorted({f"'{c['day']}'" for c in cases}))
    tids = ", ".join(f"'{c['regular_track']}'" for c in cases)
    return f"""
SELECT w.name, MIN(p.latitude) AS lat_min, MAX(p.latitude) AS lat_max, MIN(p.longitude) AS lon_min, MAX(p.longitude) AS lon_max
FROM `{FUSED}` p JOIN UNNEST([
    {rows}
  ]) w ON p.track_identifier = w.tid AND p.position_timestamp >= w.t0 AND p.position_timestamp < w.t1
WHERE DATE(p.position_timestamp) IN ({days}) AND p.valid_to IS NULL AND p.track_identifier IN ({tids})
GROUP BY w.name
"""


def boxes(cases: list[dict], dry_run: bool) -> None:
    """Box around each track's own hour of regular fusion plots."""
    sql = extents_sql(cases)
    gigabytes = dry_run_gb(sql)
    print(f"track extents: {gigabytes:.1f} GB, ${gigabytes / 1000 * PRICE_PER_TB:.2f}")
    if dry_run:
        for case in cases:
            case["box"] = dict(lat_min=case["lat"] - 1, lat_max=case["lat"] + 1, lon_min=case["lon"] - 1, lon_max=case["lon"] + 1)
        return
    extents = {r["name"]: r for r in json.loads(run_bq(sql, False) or "[]")}
    for case in cases:
        e = extents[case["name"]]
        case["box"] = dict(lat_min=round(float(e["lat_min"]) - MARGIN_DEG, 3), lat_max=round(float(e["lat_max"]) + MARGIN_DEG, 3),
                           lon_min=round(float(e["lon_min"]) - MARGIN_DEG, 3), lon_max=round(float(e["lon_max"]) + MARGIN_DEG, 3))


def source_sql(name: str, day: str, cases: list[dict], select: str) -> str:
    """All plots of one source and day that fall in any case's box and hour, tagged with the case name."""
    table, part, lat, lon, ts = TABLES[name]
    rows = ",\n    ".join(
        f"STRUCT('{c['name']}' AS case_name, TIMESTAMP('{c['t_start']}') AS t0, TIMESTAMP('{c['t_end']}') AS t1, "
        f"{c['box']['lat_min']} AS lat_min, {c['box']['lat_max']} AS lat_max, {c['box']['lon_min']} AS lon_min, {c['box']['lon_max']} AS lon_max)"
        for c in cases)
    # the same boxes as plain ranges, so tables clustered on time or position read only those blocks
    ranges = "\n     OR ".join(
        f"(t.{ts} >= TIMESTAMP('{c['t_start']}') AND t.{ts} < TIMESTAMP('{c['t_end']}') "
        f"AND t.{lat} BETWEEN {c['box']['lat_min']} AND {c['box']['lat_max']} AND t.{lon} BETWEEN {c['box']['lon_min']} AND {c['box']['lon_max']})"
        for c in cases)
    return f"""
SELECT {select} FROM `{table}` t JOIN UNNEST([
    {rows}
  ]) c ON t.{ts} >= c.t0 AND t.{ts} < c.t1 AND t.{lat} BETWEEN c.lat_min AND c.lat_max AND t.{lon} BETWEEN c.lon_min AND c.lon_max
WHERE DATE(t.{part}) = '{day}'
  AND ({ranges})
"""


def case_json(case: dict, counts: dict) -> dict:
    return dict(
        name=case["name"], day=case["day"], t_start=case["t_start"], t_end=case["t_end"], box=case["box"],
        suspect=dict(callsign=case.get("callsign"), hex=case.get("hex"), fused_track_id=case["regular_track"]),
        found_by=f"visible error finder, set {case.get('set') or 'first run'}, candidate {case['candidate']}",
        reason=case["summary"], notes=case.get("note", ""),
        flyways=dict(number=case["number"], url=case["flyways_url"], track=case["flyways_track"], notion=case.get("notion")),
        event=dict(t=pd.Timestamp(case["t_event"], unit="s").isoformat(), lat=case["lat"], lon=case["lon"], kind=case["kind"]),
        rows=counts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--count", action="store_true", help="count rows per case and source instead of pulling")
    parser.add_argument("--only", nargs="+", help="case name prefixes")
    parser.add_argument("--sources", nargs="+", choices=TABLES, help="only these sources")
    args = parser.parse_args()
    cases = json.loads(pathlib.Path(args.cases).read_text())
    if args.only:
        cases = [c for c in cases if c["name"].startswith(tuple(args.only))]

    # hour and box per case
    windows(cases)
    boxes(cases, args.dry_run)
    days = sorted({c["day"] for c in cases})
    if args.sources:
        for name in [n for n in TABLES if n not in args.sources]:
            del TABLES[name]

    # cost first: one scan per source and day
    total = 0.0
    for day in days:
        for name in TABLES:
            gigabytes = dry_run_gb(source_sql(name, day, [c for c in cases if c["day"] == day], "c.case_name, t.*"))
            total += gigabytes
            print(f"{day} {name:14s} {gigabytes:8.1f} GB  ${gigabytes / 1000 * PRICE_PER_TB:.2f}")
    print(f"total {total:.0f} GB, ${total / 1000 * PRICE_PER_TB:.2f}")
    if args.dry_run:
        return

    # rows per case and source, cheap because it reads only time and position
    if args.count:
        for day in days:
            for name in TABLES:
                sql = source_sql(name, day, [c for c in cases if c["day"] == day], "c.case_name, COUNT(*) AS n") + "GROUP BY c.case_name"
                counts = {r["case_name"]: int(r["n"]) for r in json.loads(run_bq(sql, False) or "[]")}
                print(f"{day} {name:14s} {sum(counts.values()):9d} rows  largest {max(counts.values(), default=0)}")
        return

    # then the data, split per case, one page at a time
    counts = {c["name"]: {} for c in cases}
    for day in days:
        day_cases = [c for c in cases if c["day"] == day]
        for name in TABLES:
            started = time.time()
            table, total = query_to_table(source_sql(name, day, day_cases, with_micros(name)))
            parts = {c["name"]: [] for c in day_cases}
            for frame in read_pages(table, total):
                for case_name, rows in frame.groupby("case_name") if len(frame) else []:
                    parts[case_name].append(as_strings(rows.drop(columns="case_name")))
            for case in day_cases:
                folder = HERE / case["name"]
                (folder / "sql").mkdir(parents=True, exist_ok=True)
                if parts[case["name"]]:
                    merged = pa.concat_tables(parts.pop(case["name"]), promote_options="default")
                    pq.write_table(merged, folder / f"{name}.parquet")
                    counts[case["name"]][name] = merged.num_rows
                else:
                    pd.DataFrame().to_parquet(folder / f"{name}.parquet", index=False)
                    counts[case["name"]][name] = 0
                (folder / "sql" / f"{name}.sql").write_text(source_sql(name, day, [case], "t.*") + "\n")
            print(f"{day} {name:14s} {total:9d} rows in {time.time() - started:.0f} s", flush=True)
        for case in day_cases:
            (HERE / case["name"] / "case.json").write_text(json.dumps(case_json(case, counts[case["name"]]), indent=1) + "\n")


if __name__ == "__main__":
    main()
