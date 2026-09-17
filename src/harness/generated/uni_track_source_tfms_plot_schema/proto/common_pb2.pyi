from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class FLTDMessageAttributes(_message.Message):
    __slots__ = ("acid", "airline", "arr_arpt", "cdm_part", "dep_arpt", "flight_ref", "major", "sensitivity", "source_facility", "source_timestamp")
    ACID_FIELD_NUMBER: _ClassVar[int]
    AIRLINE_FIELD_NUMBER: _ClassVar[int]
    ARR_ARPT_FIELD_NUMBER: _ClassVar[int]
    CDM_PART_FIELD_NUMBER: _ClassVar[int]
    DEP_ARPT_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_REF_FIELD_NUMBER: _ClassVar[int]
    MAJOR_FIELD_NUMBER: _ClassVar[int]
    SENSITIVITY_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FACILITY_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    acid: str
    airline: str
    arr_arpt: str
    cdm_part: str
    dep_arpt: str
    flight_ref: str
    major: str
    sensitivity: str
    source_facility: str
    source_timestamp: int
    def __init__(self, acid: _Optional[str] = ..., airline: _Optional[str] = ..., arr_arpt: _Optional[str] = ..., cdm_part: _Optional[str] = ..., dep_arpt: _Optional[str] = ..., flight_ref: _Optional[str] = ..., major: _Optional[str] = ..., sensitivity: _Optional[str] = ..., source_facility: _Optional[str] = ..., source_timestamp: _Optional[int] = ...) -> None: ...

class QualifiedAircraftID(_message.Message):
    __slots__ = ("aircraft_category", "user_category", "gufi", "aircraft_id", "computer_id__facility_identifier", "computer_id__id_number", "departure_point__airport", "arrival_point__airport")
    AIRCRAFT_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    USER_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    GUFI_FIELD_NUMBER: _ClassVar[int]
    AIRCRAFT_ID_FIELD_NUMBER: _ClassVar[int]
    COMPUTER_ID__FACILITY_IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    COMPUTER_ID__ID_NUMBER_FIELD_NUMBER: _ClassVar[int]
    DEPARTURE_POINT__AIRPORT_FIELD_NUMBER: _ClassVar[int]
    ARRIVAL_POINT__AIRPORT_FIELD_NUMBER: _ClassVar[int]
    aircraft_category: str
    user_category: str
    gufi: str
    aircraft_id: str
    computer_id__facility_identifier: str
    computer_id__id_number: str
    departure_point__airport: str
    arrival_point__airport: str
    def __init__(self, aircraft_category: _Optional[str] = ..., user_category: _Optional[str] = ..., gufi: _Optional[str] = ..., aircraft_id: _Optional[str] = ..., computer_id__facility_identifier: _Optional[str] = ..., computer_id__id_number: _Optional[str] = ..., departure_point__airport: _Optional[str] = ..., arrival_point__airport: _Optional[str] = ...) -> None: ...
