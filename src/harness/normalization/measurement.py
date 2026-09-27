"""What the normalizer hands a strategy: one Measurement per raw plot it keeps, in plain names and units, the same for every source.

A strategy reads only the Measurement, never the raw plot, so everything that depends on the source (which proto field says the
aircraft is on the ground, what the plot's accuracy is, which plots carry no real position) is decided once, in the normalizer.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Measurement:
    # the raw plot it came from, a row of raw/<source>.parquet
    source: str
    row: int

    # position
    position_us: int              # when the aircraft was there
    received_us: int              # when the plot reached us; "now" for a strategy
    source_received_us: int       # when the source received it
    lat: float
    lon: float
    altitude_ft: int | None       # barometric
    is_on_ground: bool | None     # None: the source does not say
    kind: str                     # what produced the position: own_gps, mlat, radar, report, or a plain label of its own
    accuracy_95_m: float | None   # radius of the circle that holds 95% of positions; None: not known
    time_sigma_s: float | None    # how far off the position time may be, one sigma in seconds; None: not known

    # identity
    hex: str
    callsign: str
    tail: str
    squawk: str
    track_identifier: str         # the source's own track id
    flight_number: str
    source_identifier: int        # PlotSource number, as in common.source_identifier

    # motion, for output
    ground_speed_kt: float | None
    track_deg: float | None
    heading_deg: float | None
    vertical_rate_fpm: float | None


@dataclass
class NormalizationResult:
    """What the normalizer did with one raw plot: kept it, with its Measurement, or removed it, with the reason."""
    state: str                          # kept or removed
    reason: str = ""
    measurement: Measurement | None = None

    @staticmethod
    def kept(measurement: Measurement) -> NormalizationResult:
        return NormalizationResult("kept", "", measurement)

    @staticmethod
    def removed(reason: str) -> NormalizationResult:
        return NormalizationResult("removed", reason)
