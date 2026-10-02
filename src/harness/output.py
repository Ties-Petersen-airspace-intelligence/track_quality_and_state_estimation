"""Turn what a run produced into the files the viewer reads.

The run gives two lists: per raw plot, what the normalizer and the strategy did with it; and every TrackUpdate with the time it
was emitted. From those this writes the same files, in the same columns, as when strategies emitted FusionChangedEvents, so the
viewer and production.py read both alike:
fused_plots.parquet     one row per point of every update: the update's fields, then the fused plot's fields under their proto
                        names, and valid_to
raw_plots.parquet       one row per raw plot: removed, used, skipped or rejected, why, the track and the strategy's numbers
track_state.parquet     one row per track point that has numbers: the strategy's sigmas and any other number about the track
strategy_state.parquet  the strategy's own state (numbers named state_...) per track point, for its predict()
"""
from __future__ import annotations

import pathlib

import pandas as pd
from google.protobuf.descriptor import FieldDescriptor as FD
from google.protobuf.message import Message

from . import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fused_plot_pb2 import FusedPlot
from .normalization.measurement import NormalizationResult
from .raw_plots import RawPlot
from .strategy import STATE_PREFIX, StrategyResult, TrackPoint, TrackUpdate

# column names the harness writes itself, so a strategy's number cannot take them
PLOT_COLUMNS = {"source", "row", "state", "track_id", "reason"}
TRACK_COLUMNS = {"track_id", "position_timestamp", "created_at"}


def raw_plot_row(plot: RawPlot, normalized: NormalizationResult, result: StrategyResult | None) -> dict:
    """What happened to one raw plot: removed by the normalizer, or what the strategy did with its measurement."""
    if result is None:
        return dict(source=plot.source, row=plot.row, state=normalized.state, track_id=None, reason=normalized.reason, **normalized.details)
    return dict(source=plot.source, row=plot.row, state=result.state, track_id=result.track_id, reason=result.reason, **checked(result.numbers, PLOT_COLUMNS))


def write(folder: pathlib.Path, raw_rows: list[dict], updates: list[tuple[int, TrackUpdate]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write the run's files; updates are (emitted time, update) in the order they were emitted. Returns the fused and raw plots."""
    fused = with_valid_to(pd.DataFrame(fused_rows(updates)))
    fused.to_parquet(folder / "fused_plots.parquet", index=False)
    raw = pd.DataFrame(raw_rows)
    raw.to_parquet(folder / "raw_plots.parquet", index=False)

    tracks = pd.DataFrame([dict(track_id=update.track_id, position_timestamp=point.position_us, created_at=created_at, **checked(point.numbers, TRACK_COLUMNS))
                           for created_at, update in updates for point in update.points if point.numbers])
    if not tracks.empty:
        # the strategy's own state goes to a file of its own: it only feeds predict(), and is large
        own = [c for c in tracks.columns if c.startswith(STATE_PREFIX)]
        tracks.drop(columns=own).to_parquet(folder / "track_state.parquet", index=False)
        if own:
            tracks[["track_id", "position_timestamp", "created_at"] + own].astype({c: "float32" for c in own}).to_parquet(folder / "strategy_state.parquet", index=False)
    return fused, raw


def fused_rows(updates: list[tuple[int, TrackUpdate]]) -> list[dict]:
    """One row per point: the update's fields, then every field of its fused plot under the proto name. An append has the
    quality production's append path gives it, a rewrite that of its regular fusion."""
    rows = []
    for number, (created_at, update) in enumerate(updates):
        quality = "APPEND_ONLY" if update.since == update.until and len(update.points) == 1 else "REGULAR"
        for point in update.points:
            rows.append(dict(event=number, track_id=update.track_id, created_at=created_at, quality=quality, since=update.since, until=update.until,
                             **fields(fused_plot(point))))
    return rows


def fused_plot(point: TrackPoint) -> FusedPlot:
    """The point as production's FusedPlot message, so every column has production's name and type."""
    plot = FusedPlot()
    c = plot.common
    c.source_identifier, c.track_identifier = point.source_identifier, point.track_identifier
    c.position_timestamp, c.source_received_timestamp, c.asi_received_timestamp = point.position_us, point.source_received_us, point.received_us
    c.latitude, c.longitude = point.lat, point.lon
    c.adshex, c.callsign, c.tail_number, c.squawk, c.flight_number = point.hex, point.callsign, point.tail, point.squawk, point.flight_number
    for name, value in [("altitude_ft", point.altitude_ft), ("ground_speed_kt", point.ground_speed_kt), ("track_deg", point.track_deg), ("heading_deg", point.heading_deg)]:
        if value is not None:
            setattr(c, name, value)
    if point.vertical_rate_fpm is not None:
        plot.vert_rate_fpm = point.vertical_rate_fpm
    return plot


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
    """valid_to: the created_at of the first later update on the same track whose span covers this plot's position time.
    Null means the plot is still current at the end. The viewer shows a plot when created_at <= now < valid_to."""
    frame = frame.sort_values(["track_id", "created_at", "event"]).reset_index(drop=True)
    segments = frame.drop_duplicates(["event", "since", "until"])[["track_id", "created_at", "since", "until"]]
    replaced = pd.Series(pd.NA, index=frame.index, dtype="Int64")

    # an append covers one position time: the next update on the track at that same time replaces the plot
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


def checked(numbers: dict, reserved: set[str]) -> dict:
    taken = reserved & numbers.keys()
    if taken:
        raise ValueError(f"numbers cannot be named {', '.join(sorted(taken))}; the harness writes those columns itself")
    return numbers
