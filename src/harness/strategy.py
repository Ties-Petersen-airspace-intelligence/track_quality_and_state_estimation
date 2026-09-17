"""What every contestant has to look like.

A strategy is fed raw plots one at a time, in the order we received them, and answers with
zero or more FusionChangedEvents, the same message uni-track-fusion publishes on Pulsar today.
"""
from __future__ import annotations

from typing import Protocol

from . import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import FusionChangedEvent
from .raw_plots import RawPlot


class Strategy(Protocol):
    name: str

    def on_plot(self, plot: RawPlot) -> list[FusionChangedEvent]:
        """Called once per raw plot. The plot's received_us is 'now' for the strategy."""
        ...

    def finish(self) -> list[FusionChangedEvent]:
        """Called once after the last plot, for anything still buffered."""
        ...

    def used(self, plot: RawPlot) -> str | None:
        """Called right after on_plot with the same plot. The id of the track that took this plot as a
        measurement, or None if the strategy threw it away. A state estimator that never copies plots
        still answers here, because taking a measurement in is what "used" means. Optional: a strategy
        without this method is taken to use every plot, track unknown."""
        ...
