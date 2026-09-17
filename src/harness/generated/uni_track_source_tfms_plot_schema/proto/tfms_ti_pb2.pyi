from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from uni_track_source_tfms_plot_schema.proto import common_pb2 as _common_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TFMSTrackInformationPlot(_message.Message):
    __slots__ = ("common", "fltd_message_attributes", "qualified_aircraft_id", "simple_altitude", "position_timestamp")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    FLTD_MESSAGE_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    QUALIFIED_AIRCRAFT_ID_FIELD_NUMBER: _ClassVar[int]
    SIMPLE_ALTITUDE_FIELD_NUMBER: _ClassVar[int]
    POSITION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    fltd_message_attributes: _common_pb2.FLTDMessageAttributes
    qualified_aircraft_id: _common_pb2.QualifiedAircraftID
    simple_altitude: str
    position_timestamp: int
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., fltd_message_attributes: _Optional[_Union[_common_pb2.FLTDMessageAttributes, _Mapping]] = ..., qualified_aircraft_id: _Optional[_Union[_common_pb2.QualifiedAircraftID, _Mapping]] = ..., simple_altitude: _Optional[str] = ..., position_timestamp: _Optional[int] = ...) -> None: ...
