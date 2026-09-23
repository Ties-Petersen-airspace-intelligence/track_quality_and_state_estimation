"""What every contestant has to look like.

A strategy is fed raw plots one at a time, in the order we received them, and answers each with a Result:
zero or more FusionChangedEvents, the same message uni-track-fusion publishes on Pulsar today, plus the
Outcome of that plot, what the strategy did with it and why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from . import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import FusionChangedEvent
from .raw_plots import RawPlot

# used: taken as a measurement into a track. skipped: never considered, a fixed rule says this kind of plot
# is not for this strategy. dropped: the right kind of plot, but its timing made it unusable. rejected:
# checked against a track and refused. Production runs also carry "unknown", because production does not say.
STATES = ("used", "skipped", "dropped", "rejected", "unknown")


@dataclass
class Outcome:
    state: str
    track_id: str | None = None   # the track that took the plot, or the one it was checked against
    reason: str = ""              # a few words, e.g. "type 7", "no altitude", "out of order"


@dataclass
class Result:
    events: list[FusionChangedEvent] = field(default_factory=list)
    outcome: Outcome = field(default_factory=lambda: Outcome("used"))
    # numbers the fused plot proto has no field for, one value per name, stored as extra columns of the
    # fused plots in this result: for example the filter's position sigma in metres
    fused_extras: dict[str, float] = field(default_factory=dict)


class Strategy(Protocol):
    name: str

    def on_plot(self, plot: RawPlot) -> Result:
        """Called once per raw plot. The plot's received_us is 'now' for the strategy."""
        ...

    def finish(self) -> list[FusionChangedEvent]:
        """Called once after the last plot, for anything still buffered."""
        ...
