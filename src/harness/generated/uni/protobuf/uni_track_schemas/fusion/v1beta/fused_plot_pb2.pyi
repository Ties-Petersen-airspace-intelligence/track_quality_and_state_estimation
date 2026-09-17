from uni.protobuf.uni_track_schemas.common_plot.v1beta import plot_pb2 as _plot_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FusedPlot(_message.Message):
    __slots__ = ("common", "above_ground_altitude_ft", "flight_ref", "selected_altitude_ft", "vert_rate_fpm", "pressure_hpa", "flight_id", "original_callsign", "origin", "destination")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    ABOVE_GROUND_ALTITUDE_FT_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_REF_FIELD_NUMBER: _ClassVar[int]
    SELECTED_ALTITUDE_FT_FIELD_NUMBER: _ClassVar[int]
    VERT_RATE_FPM_FIELD_NUMBER: _ClassVar[int]
    PRESSURE_HPA_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_ID_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_CALLSIGN_FIELD_NUMBER: _ClassVar[int]
    ORIGIN_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    above_ground_altitude_ft: int
    flight_ref: str
    selected_altitude_ft: int
    vert_rate_fpm: float
    pressure_hpa: float
    flight_id: str
    original_callsign: str
    origin: str
    destination: str
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., above_ground_altitude_ft: _Optional[int] = ..., flight_ref: _Optional[str] = ..., selected_altitude_ft: _Optional[int] = ..., vert_rate_fpm: _Optional[float] = ..., pressure_hpa: _Optional[float] = ..., flight_id: _Optional[str] = ..., original_callsign: _Optional[str] = ..., origin: _Optional[str] = ..., destination: _Optional[str] = ...) -> None: ...
