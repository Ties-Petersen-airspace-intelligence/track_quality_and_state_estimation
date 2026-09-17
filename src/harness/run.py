"""Run one strategy on one case and store what it emitted.

usage: uv run -m harness.run --case src/data/cases/<name> --strategy baseline

Output goes to <case>/runs/<strategy>/: events.bin holds every FusionChangedEvent as
length-prefixed protobuf bytes, and fused_plots.parquet holds one row per fused plot with the
event it came from, which is what the viewer reads.
"""
from __future__ import annotations

import argparse, pathlib, struct, time

import pandas as pd

from . import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import FusionChangedEvent, FusionQuality
from .raw_plots import load_case
from .strategies.baseline import Baseline

STRATEGIES = {"baseline": Baseline}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--strategy", required=True, choices=sorted(STRATEGIES))
    a = ap.parse_args()
    case = pathlib.Path(a.case)
    out = case / "runs" / a.strategy
    out.mkdir(parents=True, exist_ok=True)

    # load the raw plots in receipt order
    t0 = time.time()
    plots = load_case(case)
    print(f"{len(plots)} raw plots loaded in {time.time() - t0:.1f} s")

    # feed them to the strategy one by one
    strategy = STRATEGIES[a.strategy]()
    t0 = time.time()
    events = []
    for plot in plots:
        events += strategy.on_plot(plot)
    events += strategy.finish()
    print(f"{len(events)} events emitted in {time.time() - t0:.1f} s")

    # store the events exactly as protobuf, and flattened for the viewer
    write_events(events, out / "events.bin")
    rows = flatten(events)
    frame = with_valid_to(pd.DataFrame(rows))
    frame.to_parquet(out / "fused_plots.parquet", index=False)
    print(f"{len(rows)} fused plots written to {out}")


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


def flatten(events: list[FusionChangedEvent]) -> list[dict]:
    rows = []
    for i, event in enumerate(events):
        for j, segment in enumerate(event.changed_segments):
            for plot in segment.fused_track.plots:
                c = plot.common
                rows.append(dict(
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
