from uni.protobuf.uni_track_schemas.fusion.v1beta import fused_track_pb2 as _fused_track_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FusionQuality(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOT_SET: _ClassVar[FusionQuality]
    APPEND_ONLY: _ClassVar[FusionQuality]
    REGULAR: _ClassVar[FusionQuality]
    RECORRELATION: _ClassVar[FusionQuality]
NOT_SET: FusionQuality
APPEND_ONLY: FusionQuality
REGULAR: FusionQuality
RECORRELATION: FusionQuality

class Point(_message.Message):
    __slots__ = ("lat", "lon")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ...) -> None: ...

class BoundingBox(_message.Message):
    __slots__ = ("northwest", "northeast", "southwest", "southeast")
    NORTHWEST_FIELD_NUMBER: _ClassVar[int]
    NORTHEAST_FIELD_NUMBER: _ClassVar[int]
    SOUTHWEST_FIELD_NUMBER: _ClassVar[int]
    SOUTHEAST_FIELD_NUMBER: _ClassVar[int]
    northwest: Point
    northeast: Point
    southwest: Point
    southeast: Point
    def __init__(self, northwest: _Optional[_Union[Point, _Mapping]] = ..., northeast: _Optional[_Union[Point, _Mapping]] = ..., southwest: _Optional[_Union[Point, _Mapping]] = ..., southeast: _Optional[_Union[Point, _Mapping]] = ...) -> None: ...

class ChangedSegment(_message.Message):
    __slots__ = ("since", "until", "bounding_box", "fused_track")
    SINCE_FIELD_NUMBER: _ClassVar[int]
    UNTIL_FIELD_NUMBER: _ClassVar[int]
    BOUNDING_BOX_FIELD_NUMBER: _ClassVar[int]
    FUSED_TRACK_FIELD_NUMBER: _ClassVar[int]
    since: int
    until: int
    bounding_box: BoundingBox
    fused_track: _fused_track_pb2.FusedTrack
    def __init__(self, since: _Optional[int] = ..., until: _Optional[int] = ..., bounding_box: _Optional[_Union[BoundingBox, _Mapping]] = ..., fused_track: _Optional[_Union[_fused_track_pb2.FusedTrack, _Mapping]] = ...) -> None: ...

class FusionChangedEvent(_message.Message):
    __slots__ = ("track_id", "created_at", "changed_segments", "quality", "deleted_at")
    TRACK_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CHANGED_SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    QUALITY_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    track_id: str
    created_at: int
    changed_segments: _containers.RepeatedCompositeFieldContainer[ChangedSegment]
    quality: FusionQuality
    deleted_at: int
    def __init__(self, track_id: _Optional[str] = ..., created_at: _Optional[int] = ..., changed_segments: _Optional[_Iterable[_Union[ChangedSegment, _Mapping]]] = ..., quality: _Optional[_Union[FusionQuality, str]] = ..., deleted_at: _Optional[int] = ...) -> None: ...
