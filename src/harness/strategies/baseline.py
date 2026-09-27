"""The dumb baseline: every measurement becomes one fused plot, appended to a track per source track id.

No merging across sources, no filtering, no smoothing. This is the floor everything else is
compared against.
"""
from __future__ import annotations

from ..normalization.measurement import Measurement
from ..strategy import StrategyResult, TrackPoint, TrackUpdate


class Baseline:
    name = "baseline"
    params: dict = {}

    def update(self, m: Measurement) -> StrategyResult:
        # one track per source track id; the source name in front keeps ids from different sources apart
        track_id = f"{m.source}:{m.track_identifier}"

        # one point holding just this plot, copied field for field from the measurement
        point = TrackPoint(position_us=m.position_us, source_received_us=m.source_received_us, received_us=m.received_us, lat=m.lat, lon=m.lon,
                           altitude_ft=m.altitude_ft, ground_speed_kt=m.ground_speed_kt, track_deg=m.track_deg, heading_deg=m.heading_deg,
                           vertical_rate_fpm=m.vertical_rate_fpm, hex=m.hex, callsign=m.callsign, tail=m.tail, squawk=m.squawk,
                           track_identifier=m.track_identifier, flight_number=m.flight_number, source_identifier=m.source_identifier)
        return StrategyResult.used(TrackUpdate.append(track_id, point))
