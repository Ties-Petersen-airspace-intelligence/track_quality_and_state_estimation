"""The dumb baseline: every raw plot becomes one fused plot, appended to a track per source track id.

No merging across sources, no filtering, no smoothing. This is the floor everything else is
compared against.
"""
from __future__ import annotations

from .. import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import APPEND_ONLY, FusionChangedEvent
from ..raw_plots import RawPlot
from ..strategy import Outcome, Result


class Baseline:
    name = "baseline"

    def on_plot(self, plot: RawPlot) -> Result:
        common = plot.proto.common

        # one track per source track id; the source name in front keeps ids from different sources apart
        track_id = f"{plot.source}:{common.track_identifier}"
        event = FusionChangedEvent(track_id=track_id, created_at=plot.received_us, quality=APPEND_ONLY)

        # one segment holding just this plot, copied field for field from the raw common block
        segment = event.changed_segments.add(since=plot.position_us, until=plot.position_us)
        fused = segment.fused_track.plots.add()
        fused.common.ParseFromString(common.SerializeToString())
        return Result([event], Outcome("used", track_id))

    def finish(self) -> list[FusionChangedEvent]:
        return []
