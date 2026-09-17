from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UalPlot(_message.Message):
    __slots__ = ("common", "source_timestamp", "interface_version", "system_seq_number", "airline_code_cid", "airline_code_iata", "airline_code_icao", "sched_dep_date_time", "sched_dep_icao", "flight_number", "flight_leg_instance_number", "stub_flight_number", "report_datetime", "position", "speed", "altitude", "fuel", "air_temperature", "wind", "arrival_icao", "tail_number", "dispatch_desk")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_VERSION_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_SEQ_NUMBER_FIELD_NUMBER: _ClassVar[int]
    AIRLINE_CODE_CID_FIELD_NUMBER: _ClassVar[int]
    AIRLINE_CODE_IATA_FIELD_NUMBER: _ClassVar[int]
    AIRLINE_CODE_ICAO_FIELD_NUMBER: _ClassVar[int]
    SCHED_DEP_DATE_TIME_FIELD_NUMBER: _ClassVar[int]
    SCHED_DEP_ICAO_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_LEG_INSTANCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    STUB_FLIGHT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    REPORT_DATETIME_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_FIELD_NUMBER: _ClassVar[int]
    FUEL_FIELD_NUMBER: _ClassVar[int]
    AIR_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    WIND_FIELD_NUMBER: _ClassVar[int]
    ARRIVAL_ICAO_FIELD_NUMBER: _ClassVar[int]
    TAIL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    DISPATCH_DESK_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    source_timestamp: int
    interface_version: str
    system_seq_number: str
    airline_code_cid: str
    airline_code_iata: str
    airline_code_icao: str
    sched_dep_date_time: int
    sched_dep_icao: str
    flight_number: str
    flight_leg_instance_number: int
    stub_flight_number: int
    report_datetime: int
    position: str
    speed: int
    altitude: int
    fuel: int
    air_temperature: str
    wind: str
    arrival_icao: str
    tail_number: str
    dispatch_desk: str
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., source_timestamp: _Optional[int] = ..., interface_version: _Optional[str] = ..., system_seq_number: _Optional[str] = ..., airline_code_cid: _Optional[str] = ..., airline_code_iata: _Optional[str] = ..., airline_code_icao: _Optional[str] = ..., sched_dep_date_time: _Optional[int] = ..., sched_dep_icao: _Optional[str] = ..., flight_number: _Optional[str] = ..., flight_leg_instance_number: _Optional[int] = ..., stub_flight_number: _Optional[int] = ..., report_datetime: _Optional[int] = ..., position: _Optional[str] = ..., speed: _Optional[int] = ..., altitude: _Optional[int] = ..., fuel: _Optional[int] = ..., air_temperature: _Optional[str] = ..., wind: _Optional[str] = ..., arrival_icao: _Optional[str] = ..., tail_number: _Optional[str] = ..., dispatch_desk: _Optional[str] = ...) -> None: ...
