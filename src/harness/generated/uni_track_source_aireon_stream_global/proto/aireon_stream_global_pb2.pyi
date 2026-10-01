from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PositionQuality(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    POSITION_QUALITY_UNSPECIFIED: _ClassVar[PositionQuality]
    POSITION_QUALITY_LOW: _ClassVar[PositionQuality]
    POSITION_QUALITY_MEDIUM: _ClassVar[PositionQuality]
    POSITION_QUALITY_HIGH: _ClassVar[PositionQuality]

class GroundTrackReference(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GROUND_TRACK_REFERENCE_UNSPECIFIED: _ClassVar[GroundTrackReference]
    GROUND_TRACK_REFERENCE_TRUE_NORTH: _ClassVar[GroundTrackReference]
    GROUND_TRACK_REFERENCE_MAGNETIC_NORTH: _ClassVar[GroundTrackReference]
POSITION_QUALITY_UNSPECIFIED: PositionQuality
POSITION_QUALITY_LOW: PositionQuality
POSITION_QUALITY_MEDIUM: PositionQuality
POSITION_QUALITY_HIGH: PositionQuality
GROUND_TRACK_REFERENCE_UNSPECIFIED: GroundTrackReference
GROUND_TRACK_REFERENCE_TRUE_NORTH: GroundTrackReference
GROUND_TRACK_REFERENCE_MAGNETIC_NORTH: GroundTrackReference

class AireonStreamGlobalPlot(_message.Message):
    __slots__ = ("common", "is_on_ground", "barometric_altitude_ft", "geometric_altitude_ft", "barometric_vertical_rate_ft_per_min", "geometric_vertical_rate_ft_per_min", "position_quality", "surface_track_reference", "surface_ground_speed_kt", "surface_track_angle_deg")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    IS_ON_GROUND_FIELD_NUMBER: _ClassVar[int]
    BAROMETRIC_ALTITUDE_FT_FIELD_NUMBER: _ClassVar[int]
    GEOMETRIC_ALTITUDE_FT_FIELD_NUMBER: _ClassVar[int]
    BAROMETRIC_VERTICAL_RATE_FT_PER_MIN_FIELD_NUMBER: _ClassVar[int]
    GEOMETRIC_VERTICAL_RATE_FT_PER_MIN_FIELD_NUMBER: _ClassVar[int]
    POSITION_QUALITY_FIELD_NUMBER: _ClassVar[int]
    SURFACE_TRACK_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    SURFACE_GROUND_SPEED_KT_FIELD_NUMBER: _ClassVar[int]
    SURFACE_TRACK_ANGLE_DEG_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    is_on_ground: bool
    barometric_altitude_ft: int
    geometric_altitude_ft: int
    barometric_vertical_rate_ft_per_min: float
    geometric_vertical_rate_ft_per_min: float
    position_quality: PositionQuality
    surface_track_reference: GroundTrackReference
    surface_ground_speed_kt: float
    surface_track_angle_deg: float
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., is_on_ground: _Optional[bool] = ..., barometric_altitude_ft: _Optional[int] = ..., geometric_altitude_ft: _Optional[int] = ..., barometric_vertical_rate_ft_per_min: _Optional[float] = ..., geometric_vertical_rate_ft_per_min: _Optional[float] = ..., position_quality: _Optional[_Union[PositionQuality, str]] = ..., surface_track_reference: _Optional[_Union[GroundTrackReference, str]] = ..., surface_ground_speed_kt: _Optional[float] = ..., surface_track_angle_deg: _Optional[float] = ...) -> None: ...
