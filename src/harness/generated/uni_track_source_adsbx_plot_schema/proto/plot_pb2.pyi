from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ADSBXPlotType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[ADSBXPlotType]
    ADSB_ICAO: _ClassVar[ADSBXPlotType]
    ADSB_ICAO_NT: _ClassVar[ADSBXPlotType]
    ADSR_ICAO: _ClassVar[ADSBXPlotType]
    TISB_ICAO: _ClassVar[ADSBXPlotType]
    TISB_TRACKFILE: _ClassVar[ADSBXPlotType]
    ADSC: _ClassVar[ADSBXPlotType]
    MLAT: _ClassVar[ADSBXPlotType]
    MODE_S: _ClassVar[ADSBXPlotType]
    ADSB_OTHER: _ClassVar[ADSBXPlotType]
    ADSR_OTHER: _ClassVar[ADSBXPlotType]
    TISB_OTHER: _ClassVar[ADSBXPlotType]
    OTHER: _ClassVar[ADSBXPlotType]
UNKNOWN: ADSBXPlotType
ADSB_ICAO: ADSBXPlotType
ADSB_ICAO_NT: ADSBXPlotType
ADSR_ICAO: ADSBXPlotType
TISB_ICAO: ADSBXPlotType
TISB_TRACKFILE: ADSBXPlotType
ADSC: ADSBXPlotType
MLAT: ADSBXPlotType
MODE_S: ADSBXPlotType
ADSB_OTHER: ADSBXPlotType
ADSR_OTHER: ADSBXPlotType
TISB_OTHER: ADSBXPlotType
OTHER: ADSBXPlotType

class LastPosition(_message.Message):
    __slots__ = ("lat", "lon", "nic", "rc", "seen_pos")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    NIC_FIELD_NUMBER: _ClassVar[int]
    RC_FIELD_NUMBER: _ClassVar[int]
    SEEN_POS_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    nic: int
    rc: float
    seen_pos: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ..., nic: _Optional[int] = ..., rc: _Optional[float] = ..., seen_pos: _Optional[float] = ...) -> None: ...

class ADSBXPlot(_message.Message):
    __slots__ = ("common", "hex", "type", "messages", "seen", "seen_pos", "r", "t", "dbFlags", "flight", "alt_baro", "alt_geom", "gs", "ias", "tas", "mach", "track", "track_rate", "calc_track", "roll", "mag_heading", "true_heading", "baro_rate", "geom_rate", "lastPosition", "rr_lat", "rr_lon", "gpsOkBefore", "gpsOkLat", "gpsOkLon", "squawk", "emergency", "category", "version", "rc", "nic", "nic_baro", "nac_p", "nac_v", "sil", "sil_type", "gva", "sda", "nav_altitude_mcp", "nav_qnh", "nav_altitude_fms", "nav_heading", "nav_modes", "mlat", "tisb", "rssi", "alert", "spi", "wd", "ws", "oat", "tat", "acas_ra", "position_timestamp", "response_timestamp")
    COMMON_FIELD_NUMBER: _ClassVar[int]
    HEX_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    SEEN_FIELD_NUMBER: _ClassVar[int]
    SEEN_POS_FIELD_NUMBER: _ClassVar[int]
    R_FIELD_NUMBER: _ClassVar[int]
    T_FIELD_NUMBER: _ClassVar[int]
    DBFLAGS_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_FIELD_NUMBER: _ClassVar[int]
    ALT_BARO_FIELD_NUMBER: _ClassVar[int]
    ALT_GEOM_FIELD_NUMBER: _ClassVar[int]
    GS_FIELD_NUMBER: _ClassVar[int]
    IAS_FIELD_NUMBER: _ClassVar[int]
    TAS_FIELD_NUMBER: _ClassVar[int]
    MACH_FIELD_NUMBER: _ClassVar[int]
    TRACK_FIELD_NUMBER: _ClassVar[int]
    TRACK_RATE_FIELD_NUMBER: _ClassVar[int]
    CALC_TRACK_FIELD_NUMBER: _ClassVar[int]
    ROLL_FIELD_NUMBER: _ClassVar[int]
    MAG_HEADING_FIELD_NUMBER: _ClassVar[int]
    TRUE_HEADING_FIELD_NUMBER: _ClassVar[int]
    BARO_RATE_FIELD_NUMBER: _ClassVar[int]
    GEOM_RATE_FIELD_NUMBER: _ClassVar[int]
    LASTPOSITION_FIELD_NUMBER: _ClassVar[int]
    RR_LAT_FIELD_NUMBER: _ClassVar[int]
    RR_LON_FIELD_NUMBER: _ClassVar[int]
    GPSOKBEFORE_FIELD_NUMBER: _ClassVar[int]
    GPSOKLAT_FIELD_NUMBER: _ClassVar[int]
    GPSOKLON_FIELD_NUMBER: _ClassVar[int]
    SQUAWK_FIELD_NUMBER: _ClassVar[int]
    EMERGENCY_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    RC_FIELD_NUMBER: _ClassVar[int]
    NIC_FIELD_NUMBER: _ClassVar[int]
    NIC_BARO_FIELD_NUMBER: _ClassVar[int]
    NAC_P_FIELD_NUMBER: _ClassVar[int]
    NAC_V_FIELD_NUMBER: _ClassVar[int]
    SIL_FIELD_NUMBER: _ClassVar[int]
    SIL_TYPE_FIELD_NUMBER: _ClassVar[int]
    GVA_FIELD_NUMBER: _ClassVar[int]
    SDA_FIELD_NUMBER: _ClassVar[int]
    NAV_ALTITUDE_MCP_FIELD_NUMBER: _ClassVar[int]
    NAV_QNH_FIELD_NUMBER: _ClassVar[int]
    NAV_ALTITUDE_FMS_FIELD_NUMBER: _ClassVar[int]
    NAV_HEADING_FIELD_NUMBER: _ClassVar[int]
    NAV_MODES_FIELD_NUMBER: _ClassVar[int]
    MLAT_FIELD_NUMBER: _ClassVar[int]
    TISB_FIELD_NUMBER: _ClassVar[int]
    RSSI_FIELD_NUMBER: _ClassVar[int]
    ALERT_FIELD_NUMBER: _ClassVar[int]
    SPI_FIELD_NUMBER: _ClassVar[int]
    WD_FIELD_NUMBER: _ClassVar[int]
    WS_FIELD_NUMBER: _ClassVar[int]
    OAT_FIELD_NUMBER: _ClassVar[int]
    TAT_FIELD_NUMBER: _ClassVar[int]
    ACAS_RA_FIELD_NUMBER: _ClassVar[int]
    POSITION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    hex: str
    type: ADSBXPlotType
    messages: int
    seen: float
    seen_pos: float
    r: str
    t: str
    dbFlags: int
    flight: str
    alt_baro: str
    alt_geom: float
    gs: float
    ias: float
    tas: float
    mach: float
    track: float
    track_rate: float
    calc_track: float
    roll: float
    mag_heading: float
    true_heading: float
    baro_rate: float
    geom_rate: float
    lastPosition: LastPosition
    rr_lat: float
    rr_lon: float
    gpsOkBefore: float
    gpsOkLat: float
    gpsOkLon: float
    squawk: str
    emergency: str
    category: str
    version: int
    rc: float
    nic: int
    nic_baro: int
    nac_p: int
    nac_v: int
    sil: int
    sil_type: str
    gva: int
    sda: int
    nav_altitude_mcp: float
    nav_qnh: float
    nav_altitude_fms: float
    nav_heading: float
    nav_modes: _containers.RepeatedScalarFieldContainer[str]
    mlat: _containers.RepeatedScalarFieldContainer[str]
    tisb: _containers.RepeatedScalarFieldContainer[str]
    rssi: float
    alert: int
    spi: int
    wd: int
    ws: int
    oat: float
    tat: float
    acas_ra: bytes
    position_timestamp: int
    response_timestamp: int
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., hex: _Optional[str] = ..., type: _Optional[_Union[ADSBXPlotType, str]] = ..., messages: _Optional[int] = ..., seen: _Optional[float] = ..., seen_pos: _Optional[float] = ..., r: _Optional[str] = ..., t: _Optional[str] = ..., dbFlags: _Optional[int] = ..., flight: _Optional[str] = ..., alt_baro: _Optional[str] = ..., alt_geom: _Optional[float] = ..., gs: _Optional[float] = ..., ias: _Optional[float] = ..., tas: _Optional[float] = ..., mach: _Optional[float] = ..., track: _Optional[float] = ..., track_rate: _Optional[float] = ..., calc_track: _Optional[float] = ..., roll: _Optional[float] = ..., mag_heading: _Optional[float] = ..., true_heading: _Optional[float] = ..., baro_rate: _Optional[float] = ..., geom_rate: _Optional[float] = ..., lastPosition: _Optional[_Union[LastPosition, _Mapping]] = ..., rr_lat: _Optional[float] = ..., rr_lon: _Optional[float] = ..., gpsOkBefore: _Optional[float] = ..., gpsOkLat: _Optional[float] = ..., gpsOkLon: _Optional[float] = ..., squawk: _Optional[str] = ..., emergency: _Optional[str] = ..., category: _Optional[str] = ..., version: _Optional[int] = ..., rc: _Optional[float] = ..., nic: _Optional[int] = ..., nic_baro: _Optional[int] = ..., nac_p: _Optional[int] = ..., nac_v: _Optional[int] = ..., sil: _Optional[int] = ..., sil_type: _Optional[str] = ..., gva: _Optional[int] = ..., sda: _Optional[int] = ..., nav_altitude_mcp: _Optional[float] = ..., nav_qnh: _Optional[float] = ..., nav_altitude_fms: _Optional[float] = ..., nav_heading: _Optional[float] = ..., nav_modes: _Optional[_Iterable[str]] = ..., mlat: _Optional[_Iterable[str]] = ..., tisb: _Optional[_Iterable[str]] = ..., rssi: _Optional[float] = ..., alert: _Optional[int] = ..., spi: _Optional[int] = ..., wd: _Optional[int] = ..., ws: _Optional[int] = ..., oat: _Optional[float] = ..., tat: _Optional[float] = ..., acas_ra: _Optional[bytes] = ..., position_timestamp: _Optional[int] = ..., response_timestamp: _Optional[int] = ...) -> None: ...
