"""Run one strategy on one case and store what it emitted.

usage: uv run -m harness.run --case data/cases/<name> --strategy baseline [--note "..."]
       uv run -m harness.run --case data/cases --strategy baseline      # every case in the folder

Output goes to <case>/runs/<strategy>/<label>/, a fresh folder every time (labels r001, r002, ...):
fused_plots.parquet   one row per fused plot of every event, with the event's fields and valid_to
raw_plots.parquet     one row per raw plot: what the strategy did with it and why, plus its recorded numbers
track_state.parquet   one row per record.track call, when the strategy made any
run.json              what produced the run (see runs.py)
"""
from __future__ import annotations

import argparse, pathlib, time

import pandas as pd
from google.protobuf.descriptor import FieldDescriptor as FD
from google.protobuf.message import Message

from . import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import FusionChangedEvent, FusionQuality
from .raw_plots import load_case
from .strategy import Record
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
    started = time.time()

    # load the raw plots in receipt order
    plots = load_case(case)
    print(f"{case.name}: {len(plots)} raw plots loaded in {time.time() - started:.1f} s")

    # feed them to the strategy one by one, the record following along
    record = Record()
    strategy = STRATEGIES[name](record)
    t0 = time.time()
    events = []
    for plot in plots:
        record.begin(plot)
        events += strategy.on_plot(plot)
        record.end()
    events += strategy.finish()
    print(f"  {len(events)} events emitted in {time.time() - t0:.1f} s")
    if not events:
        print("  no events, no run written")
        return

    # store the fused plots, what happened to each raw plot, and the strategy's numbers about its tracks
    out = runs.new_run(case, name, runs.next_label(case, name))
    fused = with_valid_to(pd.DataFrame(flatten(events)))
    fused.to_parquet(out / "fused_plots.parquet", index=False)
    raw = pd.DataFrame(record.plots)
    raw.to_parquet(out / "raw_plots.parquet", index=False)
    if record.tracks:
        pd.DataFrame(record.tracks).to_parquet(out / "track_state.parquet", index=False)

    # what produced it, and a few counts
    counts = dict(raw_plots=len(plots), events=len(events), fused_plots=len(fused), tracks=int(fused["track_id"].nunique()), rewritten=int(fused["valid_to"].notna().sum()),
                  outcomes=raw["state"].value_counts().to_dict(), reasons=raw.loc[raw["reason"] != "", "reason"].value_counts().to_dict())
    runs.write_manifest(out, name, out.name, batch, case, params=dict(getattr(strategy, "params", {}) or {}), note=note, counts=counts, duration_s=time.time() - started, git=git)
    print(f"  {len(fused)} fused plots written to {out}; raw plots " + ", ".join(f"{k} {v}" for k, v in counts["outcomes"].items()))


def flatten(events: list[FusionChangedEvent]) -> list[dict]:
    """One row per fused plot: the event's fields, then every field of the fused plot under its proto name."""
    rows = []
    for number, event in enumerate(events):
        for segment in event.changed_segments:
            for plot in segment.fused_track.plots:
                rows.append(dict(event=number, track_id=event.track_id, created_at=event.created_at, quality=FusionQuality.Name(event.quality),
                                 since=segment.since, until=segment.until, **fields(plot)))
    return rows


def fields(message: Message) -> dict:
    """Every scalar field of a message, nested messages flattened into the same level. An optional field that
    is not set is None. Deprecated fields are left out; FusedPlot has one that shadows a Common field."""
    out = {}
    for field in message.DESCRIPTOR.fields:
        if field.GetOptions().deprecated or field.is_repeated:
            continue
        if field.type == FD.TYPE_MESSAGE:
            out.update(fields(getattr(message, field.name)))
        elif field.has_presence and not message.HasField(field.name):
            out[field.name] = None
        else:
            out[field.name] = getattr(message, field.name)
    return out


def with_valid_to(frame: pd.DataFrame) -> pd.DataFrame:
    """valid_to: the created_at of the first later event on the same track whose segment covers this plot's position time.
    Null means the plot is still current at the end. The viewer shows a plot when created_at <= now < valid_to."""
    frame = frame.sort_values(["track_id", "created_at", "event"]).reset_index(drop=True)
    segments = frame.drop_duplicates(["event", "since", "until"])[["track_id", "created_at", "since", "until"]]
    replaced = pd.Series(pd.NA, index=frame.index, dtype="Int64")

    # an append covers one position time: the next event on the track at that same time replaces the plot
    points = segments[segments["since"] == segments["until"]].rename(columns={"created_at": "replaced_at", "since": "position_timestamp"}).drop(columns="until")
    later = pd.merge_asof(frame.reset_index().sort_values("created_at"), points.sort_values("replaced_at"), left_on="created_at", right_on="replaced_at",
                          by=["track_id", "position_timestamp"], direction="forward", allow_exact_matches=False).set_index("index")["replaced_at"]
    replaced = replaced.fillna(later.astype("Int64"))

    # a rewrite covers a span: it replaces every earlier plot of its track inside the span; these are few, so loop
    for track_id, created, since, until in segments[segments["since"] < segments["until"]].itertuples(index=False):
        rows = (frame["track_id"] == track_id) & (frame["created_at"] < created) & frame["position_timestamp"].between(since, until)
        replaced[rows] = replaced[rows].fillna(created).clip(upper=created)
    frame["valid_to"] = replaced
    return frame


if __name__ == "__main__":
    main()
