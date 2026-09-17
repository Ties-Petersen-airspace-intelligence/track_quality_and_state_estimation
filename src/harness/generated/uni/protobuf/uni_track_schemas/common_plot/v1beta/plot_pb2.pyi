from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PlotSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOT_SET: _ClassVar[PlotSource]
    TFMS_TI: _ClassVar[PlotSource]
    TFMS_OR: _ClassVar[PlotSource]
    PLANEFINDER: _ClassVar[PlotSource]
    ADSBX: _ClassVar[PlotSource]
    ALASKA_ACARS: _ClassVar[PlotSource]
    UNITED_POSRPT: _ClassVar[PlotSource]
    SPIRE: _ClassVar[PlotSource]
    UDL: _ClassVar[PlotSource]
    MEIS: _ClassVar[PlotSource]
    STDDS_SMES_POSITION_REPORT: _ClassVar[PlotSource]
    UAVIONIX_FLIGHT_LINE: _ClassVar[PlotSource]
    FAA_ADSB_EDP: _ClassVar[PlotSource]
    AIREON_STREAM_GLOBAL: _ClassVar[PlotSource]
NOT_SET: PlotSource
TFMS_TI: PlotSource
TFMS_OR: PlotSource
PLANEFINDER: PlotSource
ADSBX: PlotSource
ALASKA_ACARS: PlotSource
UNITED_POSRPT: PlotSource
SPIRE: PlotSource
UDL: PlotSource
MEIS: PlotSource
STDDS_SMES_POSITION_REPORT: PlotSource
UAVIONIX_FLIGHT_LINE: PlotSource
FAA_ADSB_EDP: PlotSource
AIREON_STREAM_GLOBAL: PlotSource

class Common(_message.Message):
    __slots__ = ("longitude", "latitude", "position_timestamp", "source_received_timestamp", "asi_received_timestamp", "source_identifier", "provider_source_type", "track_identifier", "altitude_ft", "ground_speed_kt", "callsign", "tail_number", "adshex", "squawk", "ac_type", "flight_number", "heading_deg", "track_deg", "above_ground_altitude_ft", "mean_sea_level_altitude_ft")
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    POSITION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_RECEIVED_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    ASI_RECEIVED_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_SOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRACK_IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_FT_FIELD_NUMBER: _ClassVar[int]
    GROUND_SPEED_KT_FIELD_NUMBER: _ClassVar[int]
    CALLSIGN_FIELD_NUMBER: _ClassVar[int]
    TAIL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ADSHEX_FIELD_NUMBER: _ClassVar[int]
    SQUAWK_FIELD_NUMBER: _ClassVar[int]
    AC_TYPE_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    HEADING_DEG_FIELD_NUMBER: _ClassVar[int]
    TRACK_DEG_FIELD_NUMBER: _ClassVar[int]
    ABOVE_GROUND_ALTITUDE_FT_FIELD_NUMBER: _ClassVar[int]
    MEAN_SEA_LEVEL_ALTITUDE_FT_FIELD_NUMBER: _ClassVar[int]
    longitude: float
    latitude: float
    position_timestamp: int
    source_received_timestamp: int
    asi_received_timestamp: int
    source_identifier: PlotSource
    provider_source_type: int
    track_identifier: str
    altitude_ft: int
    ground_speed_kt: float
    callsign: str
    tail_number: str
    adshex: str
    squawk: str
    ac_type: str
    flight_number: str
    heading_deg: float
    track_deg: float
    above_ground_altitude_ft: int
    mean_sea_level_altitude_ft: int
    def __init__(self, longitude: _Optional[float] = ..., latitude: _Optional[float] = ..., position_timestamp: _Optional[int] = ..., source_received_timestamp: _Optional[int] = ..., asi_received_timestamp: _Optional[int] = ..., source_identifier: _Optional[_Union[PlotSource, str]] = ..., provider_source_type: _Optional[int] = ..., track_identifier: _Optional[str] = ..., altitude_ft: _Optional[int] = ..., ground_speed_kt: _Optional[float] = ..., callsign: _Optional[str] = ..., tail_number: _Optional[str] = ..., adshex: _Optional[str] = ..., squawk: _Optional[str] = ..., ac_type: _Optional[str] = ..., flight_number: _Optional[str] = ..., heading_deg: _Optional[float] = ..., track_deg: _Optional[float] = ..., above_ground_altitude_ft: _Optional[int] = ..., mean_sea_level_altitude_ft: _Optional[int] = ...) -> None: ...

class Plot(_message.Message):
    __slots__ = ("common",)
    COMMON_FIELD_NUMBER: _ClassVar[int]
    common: Common
    def __init__(self, common: _Optional[_Union[Common, _Mapping]] = ...) -> None: ...
