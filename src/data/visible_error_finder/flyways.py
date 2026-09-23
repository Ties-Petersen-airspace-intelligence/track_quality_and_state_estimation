"""Step 7: a Flyways link per candidate, pointing at regular fusion around the event.

usage: uv run data/visible_error_finder/flyways.py --list regular_spikes [--dry-run]
       uv run data/visible_error_finder/flyways.py --list flyways_trial --ratings <folder> --ids <id> <id> ...

Flyways (the ASD app) shows the hour before the snapshot time, so the snapshot is 30 minutes after
the event. The track is the regular fusion flight plan id valid at the event, else the regular
track id (AIR.<n>). Adds the links to every card of out/<list>.json, or with --ids makes that list
from the given candidates first. Run from src/.
"""
import argparse, json, pathlib, types, urllib.parse

import pandas as pd

import bq
from draw import main_track
from sets import path
from shortlist import DAYS, card, rated_candidates

HERE = pathlib.Path(__file__).parent
FLYWAYS = "https://asi.app.airspace-intelligence.com/ual/asd/#/?"
SNAPSHOT_AFTER_EVENT = pd.Timedelta(minutes=30)
FLIGHT_PLAN_SECONDS = 120   # a flight plan counts when it is on a plot this close to the event


def regular_track(candidate, plots: pd.DataFrame):
    track = main_track(plots[(plots.id == candidate.id) & (plots.fusion == "regular")], candidate)
    return None if track.empty else track.tid.iloc[0]


def flight_plans_sql(rows: list[tuple]) -> str:
    windows = ",\n    ".join(f"STRUCT('{i}' AS id, '{tid}' AS tid, {t:.3f} AS t)" for i, tid, t in rows)
    tids = ", ".join(f"'{tid}'" for _, tid, _ in rows)
    days = ", ".join(f"'{d}'" for d in DAYS)
    return f"""
WITH windows AS (SELECT * FROM UNNEST([
    {windows}
  ]))
SELECT w.id, ARRAY_AGG(p.flight_plan_id ORDER BY ABS(UNIX_MICROS(p.position_timestamp) / 1e6 - w.t) LIMIT 1)[OFFSET(0)] AS flight_plan_id
FROM `flyways.uni_track_provider.fused_plots_aws` p
JOIN windows w ON p.track_identifier = w.tid AND ABS(UNIX_MICROS(p.position_timestamp) / 1e6 - w.t) <= {FLIGHT_PLAN_SECONDS}
WHERE DATE(p.position_timestamp) IN ({days}) AND p.valid_to IS NULL AND p.track_identifier IN ({tids})
  AND p.flight_plan_id IS NOT NULL AND p.flight_plan_id != ''
GROUP BY w.id
"""


def link(t_event: float, track: str) -> tuple[str, str]:
    snapshot = (pd.Timestamp(t_event, unit="s", tz="UTC") + SNAPSHOT_AFTER_EVENT).floor("min")
    query = "timeMachine=" + urllib.parse.quote(f"{snapshot:%Y-%m-%dT%H:%M}Z;SNAPSHOT", safe="") + f"&track={track}"
    return FLYWAYS + query, f"{snapshot - pd.Timedelta(hours=1):%H:%M} to {snapshot:%H:%M} UTC"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", required=True)
    parser.add_argument("--ratings")
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    list_file = HERE / "out" / f"{args.list}.json"

    # the cards, from an existing list or made from the given candidates
    if args.ids:
        rated = rated_candidates(args.ratings).set_index("id", drop=False).loc[args.ids]
        items = [card(r) for r in rated.itertuples()]
    else:
        items = json.loads(list_file.read_text())

    # the regular fusion track of each card
    plots = pd.concat([pd.read_parquet(path(HERE / "out" / day, "plots", name))
                       for name in {item.get("set", "") for item in items} for day in DAYS])
    tracks = {item["id"]: regular_track(types.SimpleNamespace(**item), plots) for item in items}

    # the flight plan valid at the event, cost first
    rows = [(item["id"], tracks[item["id"]], item["t_event"]) for item in items if tracks[item["id"]]]
    sql = flight_plans_sql(rows)
    gigabytes, dollars = bq.cost(sql)
    print(f"flight plans: {gigabytes:.1f} GB, ${dollars:.2f}")
    if args.dry_run:
        return
    found = bq.run(sql) if rows else pd.DataFrame()
    flight_plans = dict(found.values) if not found.empty else {}

    # the link on each card
    for item in items:
        item["flyways_track"] = flight_plans.get(item["id"]) or tracks[item["id"]]
        item["flight_plan"] = item["id"] in flight_plans
        if item["flyways_track"]:
            item["flyways_url"], item["flyways_window"] = link(item["t_event"], item["flyways_track"])
    list_file.write_text(json.dumps(items, indent=1))
    print(f"{sum('flyways_url' in i for i in items)} of {len(items)} cards have a link, {len(flight_plans)} by flight plan")


if __name__ == "__main__":
    main()
