from uni.protobuf.uni_track_schemas.fusion.v1beta import fused_plot_pb2 as _fused_plot_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FusedTrack(_message.Message):
    __slots__ = ("plots",)
    PLOTS_FIELD_NUMBER: _ClassVar[int]
    plots: _containers.RepeatedCompositeFieldContainer[_fused_plot_pb2.FusedPlot]
    def __init__(self, plots: _Optional[_Iterable[_Union[_fused_plot_pb2.FusedPlot, _Mapping]]] = ...) -> None: ...

class FusedTrackBytes(_message.Message):
    __slots__ = ("plots",)
    PLOTS_FIELD_NUMBER: _ClassVar[int]
    plots: _containers.RepeatedScalarFieldContainer[bytes]
    def __init__(self, plots: _Optional[_Iterable[bytes]] = ...) -> None: ...
