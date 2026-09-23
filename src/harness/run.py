"""Run one strategy on one case and store what it emitted.

usage: uv run -m harness.run --case src/data/cases/<name> --strategy baseline [--note "..."]
       uv run -m harness.run --case src/data/cases --strategy baseline      # every case in the folder

Output goes to <case>/runs/<strategy>_append/<label>/, a fresh folder every time (labels r001, r002, ...),
the same split as production: the append path (APPEND_ONLY events) in one run, later rewrites (REGULAR
and RECORRELATION events) in <strategy>_regular. Rewrites are not supported yet; a strategy that emits one
stops the run with an error. In a run folder, events.bin holds every FusionChangedEvent as
length-prefixed protobuf bytes, fused_plots.parquet holds one row per fused plot with the event it came
from, raw_outcomes.parquet says for every raw plot what the strategy did with it (used, skipped, dropped,
rejected) and why, and run.json says what produced it (see runs.py). The viewer reads the last three.
"""
from __future__ import annotations

import argparse, pathlib, struct, time

import pandas as pd

from . import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import APPEND_ONLY, FusionChangedEvent, FusionQuality
from .raw_plots import load_case
from .strategies.baseline import Baseline
from .strategies.kalman import Kalman
from . import runs

STRATEGIES = {"baseline": Baseline, "kalman": Kalman}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, nargs="+", help="case folder(s), or a folder that holds case folders")
    ap.add_argument("--strategy", required=True, choices=sorted(STRATEGIES))
    ap.add_argument("--note", default="", help="free text stored with the run")
    a = ap.parse_args()
    batch, git = runs.new_batch(), runs.git_info()
    for case in runs.case_folders(a.case):
        run_one(case, a.strategy, a.note, batch, git)


def run_one(case: pathlib.Path, name: str, note: str, batch: str, git: dict) -> None:
    label = runs.next_label(case, name)
    started = time.time()

    # load the raw plots in receipt order
    t0 = time.time()
    plots = load_case(case)
    print(f"{case.name}: {len(plots)} raw plots loaded in {time.time() - t0:.1f} s")

    # feed them to the strategy one by one
    strategy = STRATEGIES[name]()
    t0 = time.time()
    events, outcomes, extras = [], [], []
    for plot in plots:
        result = strategy.on_plot(plot)
        events += result.events
        extras += [result.fused_extras] * len(result.events)
        outcomes.append(dict(source=plot.source, position_us=plot.position_us, source_track_identifier=plot.proto.common.track_identifier,
                             state=result.outcome.state, track_id=result.outcome.track_id, reason=result.outcome.reason))
    for event in strategy.finish():
        events.append(event); extras.append({})
    print(f"  {len(events)} events emitted in {time.time() - t0:.1f} s")

    # the append path and the rewrites are stored apart, like production's two tables
    appended = [e for e in events if e.quality == APPEND_ONLY]
    appended_extras = [x for e, x in zip(events, extras) if e.quality == APPEND_ONLY]
    if len(appended) < len(events):
        raise NotImplementedError(f"{name} emitted {len(events) - len(appended)} REGULAR or RECORRELATION events; the harness only stores the append path for now")
    if not appended:
        print("  nothing appended, no run written")
        return
    out = runs.new_run(case, name + "_append", label)

    # store the events exactly as protobuf, and flattened for the viewer
    write_events(appended, out / "events.bin")
    rows = flatten(appended, appended_extras)
    frame = with_valid_to(pd.DataFrame(rows))
    frame.to_parquet(out / "fused_plots.parquet", index=False)
    # what happened to every raw plot, and how often each state and reason occurred
    outcome_frame = pd.DataFrame(outcomes)
    outcome_frame.to_parquet(out / "raw_outcomes.parquet", index=False)
    counts = dict(raw_plots=len(plots), events=len(appended), fused_plots=len(rows), tracks=int(frame["track_id"].nunique()), rewritten=int(frame["valid_to_us"].notna().sum()),
                  outcomes=outcome_frame["state"].value_counts().to_dict(), reasons=outcome_frame.loc[outcome_frame["reason"] != "", "reason"].value_counts().to_dict())
    runs.write_manifest(out, name, label, batch, case, params=dict(getattr(strategy, "params", {}) or {}), note=note, counts=counts, duration_s=time.time() - started, git=git)
    print(f"  {len(rows)} fused plots written to {out}; raw plots " + ", ".join(f"{k} {v}" for k, v in counts["outcomes"].items()))


def write_events(events: list[FusionChangedEvent], path: pathlib.Path) -> None:
    with path.open("wb") as f:
        for event in events:
            data = event.SerializeToString()
            f.write(struct.pack("<I", len(data)))
            f.write(data)


def read_events(path: pathlib.Path) -> list[FusionChangedEvent]:
    events, data, pos = [], path.read_bytes(), 0
    while pos < len(data):
        (n,) = struct.unpack_from("<I", data, pos)
        pos += 4
        event = FusionChangedEvent()
        event.ParseFromString(data[pos:pos + n])
        events.append(event)
        pos += n
    return events


def with_valid_to(frame: pd.DataFrame) -> pd.DataFrame:
    """valid_to_us: the created_at of the first later event on the same track whose segment covers this plot's position time.
    Null means the plot is still current at the end. The viewer shows a plot when created_at <= now < valid_to."""
    frame = frame.sort_values(["track_id", "created_at_us", "event"]).reset_index(drop=True)
    valid_to = [None] * len(frame)
    for _, idx in frame.groupby("track_id", sort=False).indices.items():
        # events on this track in creation order; each (created_at, since, until)
        segs = frame.iloc[idx][["event", "created_at_us", "since_us", "until_us"]].drop_duplicates("event").to_numpy()
        for i in idx:
            created, pos = frame.at[i, "created_at_us"], frame.at[i, "position_us"]
            for ev, c, since, until in segs:
                if c > created and since <= pos <= until:
                    valid_to[i] = int(c)
                    break
    frame["valid_to_us"] = pd.array(valid_to, dtype="Int64")
    return frame


def flatten(events: list[FusionChangedEvent], extras: list[dict] | None = None) -> list[dict]:
    """One row per fused plot, with the event it came from and the strategy's extra numbers for that event."""
    rows = []
    for i, event in enumerate(events):
        for j, segment in enumerate(event.changed_segments):
            for plot in segment.fused_track.plots:
                c = plot.common
                rows.append(dict(**(extras[i] if extras else {}),
                    event=i, segment=j, track_id=event.track_id, created_at_us=event.created_at,
                    quality=FusionQuality.Name(event.quality), since_us=segment.since, until_us=segment.until,
                    position_us=c.position_timestamp, source_received_us=c.source_received_timestamp, asi_received_us=c.asi_received_timestamp,
                    source_identifier=c.source_identifier, source_track_identifier=c.track_identifier,
                    latitude=c.latitude, longitude=c.longitude,
                    altitude_ft=c.altitude_ft if c.HasField("altitude_ft") else None,
                    ground_speed_kt=c.ground_speed_kt if c.HasField("ground_speed_kt") else None,
                    heading_deg=c.heading_deg if c.HasField("heading_deg") else None,
                    track_deg=c.track_deg if c.HasField("track_deg") else None,
                    above_ground_altitude_ft=c.above_ground_altitude_ft if c.HasField("above_ground_altitude_ft") else None,
                    mean_sea_level_altitude_ft=c.mean_sea_level_altitude_ft if c.HasField("mean_sea_level_altitude_ft") else None,
                    callsign=c.callsign, tail_number=c.tail_number, adshex=c.adshex, squawk=c.squawk, ac_type=c.ac_type, flight_number=c.flight_number,
                    flight_ref=plot.flight_ref, flight_id=plot.flight_id, original_callsign=plot.original_callsign,
                ))
    return rows


if __name__ == "__main__":
    main()
