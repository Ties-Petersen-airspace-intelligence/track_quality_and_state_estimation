"""What every contestant has to look like.

A strategy is given Measurements one at a time, in the order we received the raw plots, and answers each with a StrategyResult:
what it did with the measurement and why, and the change to its tracks, a TrackUpdate, when there is one. It never sees a raw
plot: the normalizer (normalization/) turned the plot into a Measurement first, or removed it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .normalization.measurement import Measurement

# what happened to a raw plot, as raw_plots.parquet says it. removed: the normalizer took it out, no strategy saw it. used: taken
# into a track. skipped: refused by a rule on the measurement alone, without looking at a track. rejected: compared with its track
# and refused. unknown: nobody says; production never does.
STATES = ("removed", "used", "skipped", "rejected", "unknown")

# numbers of a TrackPoint named starting with this are the strategy's own state, only for its predict(); the harness stores them
# as 32-bit floats and the viewer never shows them
STATE_PREFIX = "state_"


@dataclass
class TrackPoint:
    """One point of a track, with the fields a fused plot carries. numbers are the strategy's own about the track at this point:
    its sigmas (sigma_east_m, sigma_north_m, sigma_up_m, cov_east_north_m2, sigma_speed_mps, which the viewer knows), any other
    number it wants to keep, and its state for predict() under names starting with STATE_PREFIX."""
    position_us: int
    source_received_us: int
    received_us: int
    lat: float
    lon: float
    altitude_ft: int | None = None
    ground_speed_kt: float | None = None
    track_deg: float | None = None
    heading_deg: float | None = None
    vertical_rate_fpm: float | None = None
    hex: str = ""
    callsign: str = ""
    tail: str = ""
    squawk: str = ""
    track_identifier: str = ""
    flight_number: str = ""
    source_identifier: int = 0
    numbers: dict[str, float] = field(default_factory=dict)


@dataclass
class TrackUpdate:
    """From now on, this track between since and until (position times in microseconds, both included) consists of these points.
    An append is a span that is the new point's own time, with that one point. A rewrite of history is a span in the past with
    its new points. The harness gives the update its emitted time: the received time of the measurement that caused it."""
    track_id: str
    since: int
    until: int
    points: list[TrackPoint]

    @staticmethod
    def append(track_id: str, point: TrackPoint) -> TrackUpdate:
        return TrackUpdate(track_id, point.position_us, point.position_us, [point])


@dataclass
class StrategyResult:
    """What the strategy did with one measurement. numbers are about this plot and become columns of raw_plots.parquet."""
    state: str                          # used, skipped or rejected
    reason: str = ""
    track_id: str | None = None
    numbers: dict[str, float] = field(default_factory=dict)
    update: TrackUpdate | None = None

    @staticmethod
    def used(update: TrackUpdate, **numbers) -> StrategyResult:
        return StrategyResult("used", "", update.track_id, numbers, update)

    @staticmethod
    def skipped(reason: str) -> StrategyResult:
        return StrategyResult("skipped", reason)

    @staticmethod
    def rejected(track_id: str, reason: str, **numbers) -> StrategyResult:
        return StrategyResult("rejected", reason, track_id, numbers)


class Strategy(Protocol):
    name: str
    params: dict

    def update(self, m: Measurement) -> StrategyResult:
        """Called once per kept measurement. m.received_us is 'now' for the strategy."""
        ...

# Optional: a strategy that keeps its state in its track points (numbers named state_...) can let the viewer look ahead from any
# of its fused plots with a static method on its class:
#     predict(state: dict[str, float], seconds: float, params: dict) -> dict
# giving latitude, longitude, sigma_east_m, sigma_north_m and cov_east_north_m2 of where it expects the aircraft that many
# seconds later, by its own model; params are the strategy's parameters from run.json.
