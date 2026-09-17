from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AsaPlot(_message.Message):
    __slots__ = ("common", "present_position", "last_waypoint", "system_time", "present_altitude", "goto_waypoint_id", "eta_at_goto_waypoint", "following_goto_waypoint_id", "static_air_temp", "actual_wind", "total_fuel", "ground_speed", "true_air_speed", "calibrated_air_speed", "downlink_stimulus_number", "icao_airline_code", "flight_number", "aircraft_registration", "scheduled_departure_time", "icao_departure_airport", "current_time", "message_time", "wind_speed", "wind_direction", "total_fuel_lbs", "fuel_data_update_ts", "scheduled_departure_time_ts", "eta_at_goto_waypoint_ts", "air_temperature", "true_air_speed_kt", "calibrated_air_speed_kt", "position_timestamp", "raw_position_report")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    PRESENT_POSITION_FIELD_NUMBER: _ClassVar[int]
    LAST_WAYPOINT_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_TIME_FIELD_NUMBER: _ClassVar[int]
    PRESENT_ALTITUDE_FIELD_NUMBER: _ClassVar[int]
    GOTO_WAYPOINT_ID_FIELD_NUMBER: _ClassVar[int]
    ETA_AT_GOTO_WAYPOINT_FIELD_NUMBER: _ClassVar[int]
    FOLLOWING_GOTO_WAYPOINT_ID_FIELD_NUMBER: _ClassVar[int]
    STATIC_AIR_TEMP_FIELD_NUMBER: _ClassVar[int]
    ACTUAL_WIND_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FUEL_FIELD_NUMBER: _ClassVar[int]
    GROUND_SPEED_FIELD_NUMBER: _ClassVar[int]
    TRUE_AIR_SPEED_FIELD_NUMBER: _ClassVar[int]
    CALIBRATED_AIR_SPEED_FIELD_NUMBER: _ClassVar[int]
    DOWNLINK_STIMULUS_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ICAO_AIRLINE_CODE_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    AIRCRAFT_REGISTRATION_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_DEPARTURE_TIME_FIELD_NUMBER: _ClassVar[int]
    ICAO_DEPARTURE_AIRPORT_FIELD_NUMBER: _ClassVar[int]
    CURRENT_TIME_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TIME_FIELD_NUMBER: _ClassVar[int]
    WIND_SPEED_FIELD_NUMBER: _ClassVar[int]
    WIND_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FUEL_LBS_FIELD_NUMBER: _ClassVar[int]
    FUEL_DATA_UPDATE_TS_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_DEPARTURE_TIME_TS_FIELD_NUMBER: _ClassVar[int]
    ETA_AT_GOTO_WAYPOINT_TS_FIELD_NUMBER: _ClassVar[int]
    AIR_TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TRUE_AIR_SPEED_KT_FIELD_NUMBER: _ClassVar[int]
    CALIBRATED_AIR_SPEED_KT_FIELD_NUMBER: _ClassVar[int]
    POSITION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    RAW_POSITION_REPORT_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    present_position: str
    last_waypoint: str
    system_time: str
    present_altitude: str
    goto_waypoint_id: str
    eta_at_goto_waypoint: str
    following_goto_waypoint_id: str
    static_air_temp: str
    actual_wind: str
    total_fuel: str
    ground_speed: str
    true_air_speed: str
    calibrated_air_speed: str
    downlink_stimulus_number: str
    icao_airline_code: str
    flight_number: str
    aircraft_registration: str
    scheduled_departure_time: str
    icao_departure_airport: str
    current_time: str
    message_time: str
    wind_speed: int
    wind_direction: int
    total_fuel_lbs: int
    fuel_data_update_ts: int
    scheduled_departure_time_ts: int
    eta_at_goto_waypoint_ts: int
    air_temperature: int
    true_air_speed_kt: int
    calibrated_air_speed_kt: int
    position_timestamp: int
    raw_position_report: str
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., present_position: _Optional[str] = ..., last_waypoint: _Optional[str] = ..., system_time: _Optional[str] = ..., present_altitude: _Optional[str] = ..., goto_waypoint_id: _Optional[str] = ..., eta_at_goto_waypoint: _Optional[str] = ..., following_goto_waypoint_id: _Optional[str] = ..., static_air_temp: _Optional[str] = ..., actual_wind: _Optional[str] = ..., total_fuel: _Optional[str] = ..., ground_speed: _Optional[str] = ..., true_air_speed: _Optional[str] = ..., calibrated_air_speed: _Optional[str] = ..., downlink_stimulus_number: _Optional[str] = ..., icao_airline_code: _Optional[str] = ..., flight_number: _Optional[str] = ..., aircraft_registration: _Optional[str] = ..., scheduled_departure_time: _Optional[str] = ..., icao_departure_airport: _Optional[str] = ..., current_time: _Optional[str] = ..., message_time: _Optional[str] = ..., wind_speed: _Optional[int] = ..., wind_direction: _Optional[int] = ..., total_fuel_lbs: _Optional[int] = ..., fuel_data_update_ts: _Optional[int] = ..., scheduled_departure_time_ts: _Optional[int] = ..., eta_at_goto_waypoint_ts: _Optional[int] = ..., air_temperature: _Optional[int] = ..., true_air_speed_kt: _Optional[int] = ..., calibrated_air_speed_kt: _Optional[int] = ..., position_timestamp: _Optional[int] = ..., raw_position_report: _Optional[str] = ...) -> None: ...
