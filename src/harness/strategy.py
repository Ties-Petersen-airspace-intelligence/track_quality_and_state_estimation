"""What every contestant has to look like.

A strategy is fed raw plots one at a time, in the order we received them, and answers each with zero or more
FusionChangedEvents, the same message uni-track-fusion publishes on Pulsar today. Next to that it keeps a Record,
handed to it once when it is made: what it did with each raw plot and why, and any numbers it wants to keep
about its tracks, such as the filter's uncertainty.
"""
from __future__ import annotations

from typing import Protocol

from . import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import FusionChangedEvent
from .raw_plots import RawPlot

# used: taken as a measurement into a track. skipped: never considered, a fixed rule says this kind of plot
# is not for this strategy. dropped: the right kind of plot, but its timing made it unusable. rejected:
# checked against a track and refused. unknown: the strategy recorded nothing, and production never says.
STATES = ("used", "skipped", "dropped", "rejected", "unknown")


class Record:
    """The strategy's notes next to its events. The harness points it at the current raw plot before each
    on_plot call, so a strategy only says what happened: one of used, skipped, dropped or rejected per raw
    plot, and track(...) whenever it has numbers about a track. Extra keyword numbers become columns:
    on the raw plot's row for the first four, on the track's row for track()."""

    def __init__(self):
        self.plots: list[dict] = []    # one row per raw plot
        self.tracks: list[dict] = []   # one row per track() call
        self.current: RawPlot | None = None
        self.outcome: dict | None = None

    def used(self, track_id: str, **numbers) -> None:
        self._outcome("used", track_id, "", numbers)

    def skipped(self, reason: str) -> None:
        self._outcome("skipped", None, reason, {})

    def dropped(self, reason: str, track_id: str | None = None, **numbers) -> None:
        self._outcome("dropped", track_id, reason, numbers)

    def rejected(self, track_id: str, reason: str, **numbers) -> None:
        self._outcome("rejected", track_id, reason, numbers)

    def track(self, track_id: str, **numbers) -> None:
        """Numbers about a track as of the current plot, matched in the viewer to the fused plot of the same track,
        position time and emission time."""
        plot = self._plot("track")
        self.tracks.append(dict(track_id=track_id, position_timestamp=plot.position_us, created_at=plot.received_us, **checked(numbers, TRACK_COLUMNS)))

    # called by the harness

    def begin(self, plot: RawPlot) -> None:
        self.current, self.outcome = plot, None

    def end(self) -> None:
        """Store the current plot's outcome; a plot the strategy said nothing about is unknown."""
        plot = self.current
        outcome = self.outcome or dict(state="unknown", track_id=None, reason="")
        self.plots.append(dict(source=plot.source, row=plot.row, **outcome))
        self.current = self.outcome = None

    def _plot(self, call: str) -> RawPlot:
        if self.current is None:
            raise ValueError(f"record.{call} called outside on_plot; the record only knows the raw plot on_plot is handling")
        return self.current

    def _outcome(self, state: str, track_id: str | None, reason: str, numbers: dict) -> None:
        plot = self._plot(state)
        if self.outcome is not None:
            raise ValueError(f"raw plot {plot.source} row {plot.row} recorded twice: {self.outcome['state']}, then {state}")
        self.outcome = dict(state=state, track_id=track_id, reason=reason, **checked(numbers, PLOT_COLUMNS))


# column names the harness writes itself, so a recorded number cannot take them
PLOT_COLUMNS = {"source", "row", "state", "track_id", "reason"}
TRACK_COLUMNS = {"track_id", "position_timestamp", "created_at"}


def checked(numbers: dict, reserved: set[str]) -> dict:
    taken = reserved & numbers.keys()
    if taken:
        raise ValueError(f"recorded numbers cannot be named {', '.join(sorted(taken))}; the harness writes those columns itself")
    return numbers


class Strategy(Protocol):
    name: str

    def __init__(self, record: Record):
        ...

    def on_plot(self, plot: RawPlot) -> list[FusionChangedEvent]:
        """Called once per raw plot. The plot's received_us is 'now' for the strategy."""
        ...

    def finish(self) -> list[FusionChangedEvent]:
        """Called once after the last plot, for anything still buffered."""
        ...
