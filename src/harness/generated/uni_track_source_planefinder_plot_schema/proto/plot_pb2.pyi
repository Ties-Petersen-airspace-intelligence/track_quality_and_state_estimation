from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DataSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[DataSource]
    ADSB: _ClassVar[DataSource]
    PLANE_FINDER_MLAT: _ClassVar[DataSource]
    FLARM: _ClassVar[DataSource]
    THIRD_PARTY_DERIVED_MLAT: _ClassVar[DataSource]
    BLOCKED_DATA: _ClassVar[DataSource]
UNKNOWN: DataSource
ADSB: DataSource
PLANE_FINDER_MLAT: DataSource
FLARM: DataSource
THIRD_PARTY_DERIVED_MLAT: DataSource
BLOCKED_DATA: DataSource

class PlanefinderPlot(_message.Message):
    __slots__ = ("common", "speed", "altitude", "is_on_ground", "pos_update_time", "vert_rate", "selected_altitude", "roll_angle", "gs", "ias", "tas", "mach", "heading", "magnetic_heading", "target_heading", "track_angle", "oat", "barometer", "wind_speed", "wind_direction", "data_source", "reg", "ac_type", "category", "last_seen_time", "flight_number", "original_callsign", "callsign", "route", "is_blocked", "station_id")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_FIELD_NUMBER: _ClassVar[int]
    IS_ON_GROUND_FIELD_NUMBER: _ClassVar[int]
    POS_UPDATE_TIME_FIELD_NUMBER: _ClassVar[int]
    VERT_RATE_FIELD_NUMBER: _ClassVar[int]
    SELECTED_ALTITUDE_FIELD_NUMBER: _ClassVar[int]
    ROLL_ANGLE_FIELD_NUMBER: _ClassVar[int]
    GS_FIELD_NUMBER: _ClassVar[int]
    IAS_FIELD_NUMBER: _ClassVar[int]
    TAS_FIELD_NUMBER: _ClassVar[int]
    MACH_FIELD_NUMBER: _ClassVar[int]
    HEADING_FIELD_NUMBER: _ClassVar[int]
    MAGNETIC_HEADING_FIELD_NUMBER: _ClassVar[int]
    TARGET_HEADING_FIELD_NUMBER: _ClassVar[int]
    TRACK_ANGLE_FIELD_NUMBER: _ClassVar[int]
    OAT_FIELD_NUMBER: _ClassVar[int]
    BAROMETER_FIELD_NUMBER: _ClassVar[int]
    WIND_SPEED_FIELD_NUMBER: _ClassVar[int]
    WIND_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    DATA_SOURCE_FIELD_NUMBER: _ClassVar[int]
    REG_FIELD_NUMBER: _ClassVar[int]
    AC_TYPE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    LAST_SEEN_TIME_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_CALLSIGN_FIELD_NUMBER: _ClassVar[int]
    CALLSIGN_FIELD_NUMBER: _ClassVar[int]
    ROUTE_FIELD_NUMBER: _ClassVar[int]
    IS_BLOCKED_FIELD_NUMBER: _ClassVar[int]
    STATION_ID_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    speed: int
    altitude: int
    is_on_ground: bool
    pos_update_time: int
    vert_rate: int
    selected_altitude: int
    roll_angle: float
    gs: int
    ias: int
    tas: int
    mach: float
    heading: int
    magnetic_heading: int
    target_heading: int
    track_angle: int
    oat: float
    barometer: float
    wind_speed: int
    wind_direction: int
    data_source: DataSource
    reg: str
    ac_type: str
    category: str
    last_seen_time: int
    flight_number: str
    original_callsign: str
    callsign: str
    route: str
    is_blocked: bool
    station_id: str
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., speed: _Optional[int] = ..., altitude: _Optional[int] = ..., is_on_ground: _Optional[bool] = ..., pos_update_time: _Optional[int] = ..., vert_rate: _Optional[int] = ..., selected_altitude: _Optional[int] = ..., roll_angle: _Optional[float] = ..., gs: _Optional[int] = ..., ias: _Optional[int] = ..., tas: _Optional[int] = ..., mach: _Optional[float] = ..., heading: _Optional[int] = ..., magnetic_heading: _Optional[int] = ..., target_heading: _Optional[int] = ..., track_angle: _Optional[int] = ..., oat: _Optional[float] = ..., barometer: _Optional[float] = ..., wind_speed: _Optional[int] = ..., wind_direction: _Optional[int] = ..., data_source: _Optional[_Union[DataSource, str]] = ..., reg: _Optional[str] = ..., ac_type: _Optional[str] = ..., category: _Optional[str] = ..., last_seen_time: _Optional[int] = ..., flight_number: _Optional[str] = ..., original_callsign: _Optional[str] = ..., callsign: _Optional[str] = ..., route: _Optional[str] = ..., is_blocked: _Optional[bool] = ..., station_id: _Optional[str] = ...) -> None: ...
