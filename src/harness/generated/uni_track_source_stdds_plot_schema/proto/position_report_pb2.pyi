from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PositionReport(_message.Message):
    __slots__ = ("common", "is_full", "airport", "seq_num", "time", "track", "stid", "flight_id", "enhanced_data", "flight_info", "manual", "movement", "position", "slc", "status", "target_extent", "plot_count", "position_timestamp")
    class FlightId(_message.Message):
        __slots__ = ("ac_address", "aircraft_id", "mode_3_a_code")
        AC_ADDRESS_FIELD_NUMBER: _ClassVar[int]
        AIRCRAFT_ID_FIELD_NUMBER: _ClassVar[int]
        MODE_3_A_CODE_FIELD_NUMBER: _ClassVar[int]
        ac_address: str
        aircraft_id: str
        mode_3_a_code: str
        def __init__(self, ac_address: _Optional[str] = ..., aircraft_id: _Optional[str] = ..., mode_3_a_code: _Optional[str] = ...) -> None: ...
    class EnhancedData(_message.Message):
        __slots__ = ("eram_gufi", "sfdps_gufi", "departure_airport", "destination_airport", "aircraft_type", "beacon_code")
        ERAM_GUFI_FIELD_NUMBER: _ClassVar[int]
        SFDPS_GUFI_FIELD_NUMBER: _ClassVar[int]
        DEPARTURE_AIRPORT_FIELD_NUMBER: _ClassVar[int]
        DESTINATION_AIRPORT_FIELD_NUMBER: _ClassVar[int]
        AIRCRAFT_TYPE_FIELD_NUMBER: _ClassVar[int]
        BEACON_CODE_FIELD_NUMBER: _ClassVar[int]
        eram_gufi: str
        sfdps_gufi: str
        departure_airport: str
        destination_airport: str
        aircraft_type: str
        beacon_code: str
        def __init__(self, eram_gufi: _Optional[str] = ..., sfdps_gufi: _Optional[str] = ..., departure_airport: _Optional[str] = ..., destination_airport: _Optional[str] = ..., aircraft_type: _Optional[str] = ..., beacon_code: _Optional[str] = ...) -> None: ...
    class FlightInfo(_message.Message):
        __slots__ = ("ac_type", "fix", "runway", "tgt_type", "wake")
        class TargetType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            TT_UNSPECIFIED: _ClassVar[PositionReport.FlightInfo.TargetType]
            TT_UNKNOWN: _ClassVar[PositionReport.FlightInfo.TargetType]
            TT_AIRCRAFT: _ClassVar[PositionReport.FlightInfo.TargetType]
            TT_VEHICLE: _ClassVar[PositionReport.FlightInfo.TargetType]
            TT_UNKNOWN_AIRCRAFT: _ClassVar[PositionReport.FlightInfo.TargetType]
        TT_UNSPECIFIED: PositionReport.FlightInfo.TargetType
        TT_UNKNOWN: PositionReport.FlightInfo.TargetType
        TT_AIRCRAFT: PositionReport.FlightInfo.TargetType
        TT_VEHICLE: PositionReport.FlightInfo.TargetType
        TT_UNKNOWN_AIRCRAFT: PositionReport.FlightInfo.TargetType
        AC_TYPE_FIELD_NUMBER: _ClassVar[int]
        FIX_FIELD_NUMBER: _ClassVar[int]
        RUNWAY_FIELD_NUMBER: _ClassVar[int]
        TGT_TYPE_FIELD_NUMBER: _ClassVar[int]
        WAKE_FIELD_NUMBER: _ClassVar[int]
        ac_type: str
        fix: str
        runway: str
        tgt_type: PositionReport.FlightInfo.TargetType
        wake: str
        def __init__(self, ac_type: _Optional[str] = ..., fix: _Optional[str] = ..., runway: _Optional[str] = ..., tgt_type: _Optional[_Union[PositionReport.FlightInfo.TargetType, str]] = ..., wake: _Optional[str] = ...) -> None: ...
    class Manual(_message.Message):
        __slots__ = ("ac_type", "call_num", "category", "fix", "mode_3_a_code", "scratchpad_1", "scratchpad_2")
        AC_TYPE_FIELD_NUMBER: _ClassVar[int]
        CALL_NUM_FIELD_NUMBER: _ClassVar[int]
        CATEGORY_FIELD_NUMBER: _ClassVar[int]
        FIX_FIELD_NUMBER: _ClassVar[int]
        MODE_3_A_CODE_FIELD_NUMBER: _ClassVar[int]
        SCRATCHPAD_1_FIELD_NUMBER: _ClassVar[int]
        SCRATCHPAD_2_FIELD_NUMBER: _ClassVar[int]
        ac_type: str
        call_num: str
        category: str
        fix: str
        mode_3_a_code: str
        scratchpad_1: str
        scratchpad_2: str
        def __init__(self, ac_type: _Optional[str] = ..., call_num: _Optional[str] = ..., category: _Optional[str] = ..., fix: _Optional[str] = ..., mode_3_a_code: _Optional[str] = ..., scratchpad_1: _Optional[str] = ..., scratchpad_2: _Optional[str] = ...) -> None: ...
    class Movement(_message.Message):
        __slots__ = ("ax", "ay", "heading", "speed", "vx", "vy")
        AX_FIELD_NUMBER: _ClassVar[int]
        AY_FIELD_NUMBER: _ClassVar[int]
        HEADING_FIELD_NUMBER: _ClassVar[int]
        SPEED_FIELD_NUMBER: _ClassVar[int]
        VX_FIELD_NUMBER: _ClassVar[int]
        VY_FIELD_NUMBER: _ClassVar[int]
        ax: float
        ay: float
        heading: float
        speed: int
        vx: float
        vy: float
        def __init__(self, ax: _Optional[float] = ..., ay: _Optional[float] = ..., heading: _Optional[float] = ..., speed: _Optional[int] = ..., vx: _Optional[float] = ..., vy: _Optional[float] = ...) -> None: ...
    class Position(_message.Message):
        __slots__ = ("altitude", "extended_x", "extended_y", "flight_level", "latitude", "longitude", "x", "y")
        ALTITUDE_FIELD_NUMBER: _ClassVar[int]
        EXTENDED_X_FIELD_NUMBER: _ClassVar[int]
        EXTENDED_Y_FIELD_NUMBER: _ClassVar[int]
        FLIGHT_LEVEL_FIELD_NUMBER: _ClassVar[int]
        LATITUDE_FIELD_NUMBER: _ClassVar[int]
        LONGITUDE_FIELD_NUMBER: _ClassVar[int]
        X_FIELD_NUMBER: _ClassVar[int]
        Y_FIELD_NUMBER: _ClassVar[int]
        altitude: float
        extended_x: int
        extended_y: int
        flight_level: float
        latitude: float
        longitude: float
        x: int
        y: int
        def __init__(self, altitude: _Optional[float] = ..., extended_x: _Optional[int] = ..., extended_y: _Optional[int] = ..., flight_level: _Optional[float] = ..., latitude: _Optional[float] = ..., longitude: _Optional[float] = ..., x: _Optional[int] = ..., y: _Optional[int] = ...) -> None: ...
    class Slc(_message.Message):
        __slots__ = ("coast_num", "local_av_num", "susp_num")
        COAST_NUM_FIELD_NUMBER: _ClassVar[int]
        LOCAL_AV_NUM_FIELD_NUMBER: _ClassVar[int]
        SUSP_NUM_FIELD_NUMBER: _ClassVar[int]
        coast_num: int
        local_av_num: int
        susp_num: int
        def __init__(self, coast_num: _Optional[int] = ..., local_av_num: _Optional[int] = ..., susp_num: _Optional[int] = ...) -> None: ...
    class Status(_message.Message):
        __slots__ = ("a9s", "af", "ap", "aq", "aq1090", "aq_uat", "at", "da", "df", "di", "gbs", "gm", "ls", "lv", "lv_1090", "lv_uat", "m3c", "mon", "mrh", "ms", "nc", "op", "quality", "rt", "s1", "si", "sim", "spi", "src", "ss", "st", "su", "tc", "tf", "twy_id", "aa", "av", "sil", "nic", "nacp", "vs", "ud", "vert_rate", "uncorr_baro_alt", "tse", "ua", "x")
        class AlertFilter(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            AF_UNSPECIFIED: _ClassVar[PositionReport.Status.AlertFilter]
            AF_UNFILTERED: _ClassVar[PositionReport.Status.AlertFilter]
            AF_FILTERED: _ClassVar[PositionReport.Status.AlertFilter]
            AF_HIGHLIGHT: _ClassVar[PositionReport.Status.AlertFilter]
        AF_UNSPECIFIED: PositionReport.Status.AlertFilter
        AF_UNFILTERED: PositionReport.Status.AlertFilter
        AF_FILTERED: PositionReport.Status.AlertFilter
        AF_HIGHLIGHT: PositionReport.Status.AlertFilter
        class AddressQualifier(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            AQ_UNSPECIFIED: _ClassVar[PositionReport.Status.AddressQualifier]
            AQ_ADSBICAO: _ClassVar[PositionReport.Status.AddressQualifier]
            AQ_ADSBSA: _ClassVar[PositionReport.Status.AddressQualifier]
            AQ_TISBICAO: _ClassVar[PositionReport.Status.AddressQualifier]
            AQ_TISBTFI: _ClassVar[PositionReport.Status.AddressQualifier]
            AQ_VEHICLE: _ClassVar[PositionReport.Status.AddressQualifier]
            AQ_BEACON: _ClassVar[PositionReport.Status.AddressQualifier]
        AQ_UNSPECIFIED: PositionReport.Status.AddressQualifier
        AQ_ADSBICAO: PositionReport.Status.AddressQualifier
        AQ_ADSBSA: PositionReport.Status.AddressQualifier
        AQ_TISBICAO: PositionReport.Status.AddressQualifier
        AQ_TISBTFI: PositionReport.Status.AddressQualifier
        AQ_VEHICLE: PositionReport.Status.AddressQualifier
        AQ_BEACON: PositionReport.Status.AddressQualifier
        class AltitudeDerivationSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ADS_UNSPECIFIED: _ClassVar[PositionReport.Status.AltitudeDerivationSource]
            ADS_BAROMETRIC: _ClassVar[PositionReport.Status.AltitudeDerivationSource]
            ADS_GEOMETRIC: _ClassVar[PositionReport.Status.AltitudeDerivationSource]
        ADS_UNSPECIFIED: PositionReport.Status.AltitudeDerivationSource
        ADS_BAROMETRIC: PositionReport.Status.AltitudeDerivationSource
        ADS_GEOMETRIC: PositionReport.Status.AltitudeDerivationSource
        class FusedHeightSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            FHS_UNSPECIFIED: _ClassVar[PositionReport.Status.FusedHeightSource]
            FHS_NONE: _ClassVar[PositionReport.Status.FusedHeightSource]
            FHS_ADSB: _ClassVar[PositionReport.Status.FusedHeightSource]
            FHS_MODEC: _ClassVar[PositionReport.Status.FusedHeightSource]
            FHS_MULTILAT: _ClassVar[PositionReport.Status.FusedHeightSource]
            FHS_GROUND: _ClassVar[PositionReport.Status.FusedHeightSource]
            FHS_MULTIPLE: _ClassVar[PositionReport.Status.FusedHeightSource]
        FHS_UNSPECIFIED: PositionReport.Status.FusedHeightSource
        FHS_NONE: PositionReport.Status.FusedHeightSource
        FHS_ADSB: PositionReport.Status.FusedHeightSource
        FHS_MODEC: PositionReport.Status.FusedHeightSource
        FHS_MULTILAT: PositionReport.Status.FusedHeightSource
        FHS_GROUND: PositionReport.Status.FusedHeightSource
        FHS_MULTIPLE: PositionReport.Status.FusedHeightSource
        class CoordinateValidationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            CVS_UNSPECIFIED: _ClassVar[PositionReport.Status.CoordinateValidationStatus]
            CVS_UNKNOWN: _ClassVar[PositionReport.Status.CoordinateValidationStatus]
            CVS_INVALID: _ClassVar[PositionReport.Status.CoordinateValidationStatus]
            CVS_RESERVED: _ClassVar[PositionReport.Status.CoordinateValidationStatus]
            CVS_VALID: _ClassVar[PositionReport.Status.CoordinateValidationStatus]
        CVS_UNSPECIFIED: PositionReport.Status.CoordinateValidationStatus
        CVS_UNKNOWN: PositionReport.Status.CoordinateValidationStatus
        CVS_INVALID: PositionReport.Status.CoordinateValidationStatus
        CVS_RESERVED: PositionReport.Status.CoordinateValidationStatus
        CVS_VALID: PositionReport.Status.CoordinateValidationStatus
        class Direction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DIRECTION_UNSPECIFIED: _ClassVar[PositionReport.Status.Direction]
            DIRECTION_UP: _ClassVar[PositionReport.Status.Direction]
            DIRECTION_DOWN: _ClassVar[PositionReport.Status.Direction]
        DIRECTION_UNSPECIFIED: PositionReport.Status.Direction
        DIRECTION_UP: PositionReport.Status.Direction
        DIRECTION_DOWN: PositionReport.Status.Direction
        A9S_FIELD_NUMBER: _ClassVar[int]
        AF_FIELD_NUMBER: _ClassVar[int]
        AP_FIELD_NUMBER: _ClassVar[int]
        AQ_FIELD_NUMBER: _ClassVar[int]
        AQ1090_FIELD_NUMBER: _ClassVar[int]
        AQ_UAT_FIELD_NUMBER: _ClassVar[int]
        AS_FIELD_NUMBER: _ClassVar[int]
        AT_FIELD_NUMBER: _ClassVar[int]
        DA_FIELD_NUMBER: _ClassVar[int]
        DF_FIELD_NUMBER: _ClassVar[int]
        DI_FIELD_NUMBER: _ClassVar[int]
        GBS_FIELD_NUMBER: _ClassVar[int]
        GM_FIELD_NUMBER: _ClassVar[int]
        LS_FIELD_NUMBER: _ClassVar[int]
        LV_FIELD_NUMBER: _ClassVar[int]
        LV_1090_FIELD_NUMBER: _ClassVar[int]
        LV_UAT_FIELD_NUMBER: _ClassVar[int]
        M3C_FIELD_NUMBER: _ClassVar[int]
        MON_FIELD_NUMBER: _ClassVar[int]
        MRH_FIELD_NUMBER: _ClassVar[int]
        MS_FIELD_NUMBER: _ClassVar[int]
        NC_FIELD_NUMBER: _ClassVar[int]
        OP_FIELD_NUMBER: _ClassVar[int]
        QUALITY_FIELD_NUMBER: _ClassVar[int]
        RT_FIELD_NUMBER: _ClassVar[int]
        S1_FIELD_NUMBER: _ClassVar[int]
        SI_FIELD_NUMBER: _ClassVar[int]
        SIM_FIELD_NUMBER: _ClassVar[int]
        SPI_FIELD_NUMBER: _ClassVar[int]
        SRC_FIELD_NUMBER: _ClassVar[int]
        SS_FIELD_NUMBER: _ClassVar[int]
        ST_FIELD_NUMBER: _ClassVar[int]
        SU_FIELD_NUMBER: _ClassVar[int]
        TC_FIELD_NUMBER: _ClassVar[int]
        TF_FIELD_NUMBER: _ClassVar[int]
        TWY_ID_FIELD_NUMBER: _ClassVar[int]
        AA_FIELD_NUMBER: _ClassVar[int]
        AV_FIELD_NUMBER: _ClassVar[int]
        SIL_FIELD_NUMBER: _ClassVar[int]
        NIC_FIELD_NUMBER: _ClassVar[int]
        NACP_FIELD_NUMBER: _ClassVar[int]
        VS_FIELD_NUMBER: _ClassVar[int]
        UD_FIELD_NUMBER: _ClassVar[int]
        VERT_RATE_FIELD_NUMBER: _ClassVar[int]
        UNCORR_BARO_ALT_FIELD_NUMBER: _ClassVar[int]
        TSE_FIELD_NUMBER: _ClassVar[int]
        UA_FIELD_NUMBER: _ClassVar[int]
        X_FIELD_NUMBER: _ClassVar[int]
        a9s: int
        af: PositionReport.Status.AlertFilter
        ap: int
        aq: int
        aq1090: PositionReport.Status.AddressQualifier
        aq_uat: PositionReport.Status.AddressQualifier
        at: int
        da: int
        df: int
        di: int
        gbs: int
        gm: int
        ls: int
        lv: int
        lv_1090: int
        lv_uat: int
        m3c: int
        mon: int
        mrh: PositionReport.Status.AltitudeDerivationSource
        ms: int
        nc: int
        op: int
        quality: int
        rt: int
        s1: int
        si: int
        sim: int
        spi: int
        src: PositionReport.Status.FusedHeightSource
        ss: int
        st: int
        su: int
        tc: int
        tf: int
        twy_id: int
        aa: int
        av: PositionReport.Status.CoordinateValidationStatus
        sil: int
        nic: int
        nacp: int
        vs: PositionReport.Status.AltitudeDerivationSource
        ud: PositionReport.Status.Direction
        vert_rate: int
        uncorr_baro_alt: int
        tse: int
        ua: int
        x: int
        def __init__(self, a9s: _Optional[int] = ..., af: _Optional[_Union[PositionReport.Status.AlertFilter, str]] = ..., ap: _Optional[int] = ..., aq: _Optional[int] = ..., aq1090: _Optional[_Union[PositionReport.Status.AddressQualifier, str]] = ..., aq_uat: _Optional[_Union[PositionReport.Status.AddressQualifier, str]] = ..., at: _Optional[int] = ..., da: _Optional[int] = ..., df: _Optional[int] = ..., di: _Optional[int] = ..., gbs: _Optional[int] = ..., gm: _Optional[int] = ..., ls: _Optional[int] = ..., lv: _Optional[int] = ..., lv_1090: _Optional[int] = ..., lv_uat: _Optional[int] = ..., m3c: _Optional[int] = ..., mon: _Optional[int] = ..., mrh: _Optional[_Union[PositionReport.Status.AltitudeDerivationSource, str]] = ..., ms: _Optional[int] = ..., nc: _Optional[int] = ..., op: _Optional[int] = ..., quality: _Optional[int] = ..., rt: _Optional[int] = ..., s1: _Optional[int] = ..., si: _Optional[int] = ..., sim: _Optional[int] = ..., spi: _Optional[int] = ..., src: _Optional[_Union[PositionReport.Status.FusedHeightSource, str]] = ..., ss: _Optional[int] = ..., st: _Optional[int] = ..., su: _Optional[int] = ..., tc: _Optional[int] = ..., tf: _Optional[int] = ..., twy_id: _Optional[int] = ..., aa: _Optional[int] = ..., av: _Optional[_Union[PositionReport.Status.CoordinateValidationStatus, str]] = ..., sil: _Optional[int] = ..., nic: _Optional[int] = ..., nacp: _Optional[int] = ..., vs: _Optional[_Union[PositionReport.Status.AltitudeDerivationSource, str]] = ..., ud: _Optional[_Union[PositionReport.Status.Direction, str]] = ..., vert_rate: _Optional[int] = ..., uncorr_baro_alt: _Optional[int] = ..., tse: _Optional[int] = ..., ua: _Optional[int] = ..., x: _Optional[int] = ..., **kwargs) -> None: ...
    class TargetExtent(_message.Message):
        __slots__ = ("start_azimuth", "start_range", "end_azimuth", "end_range", "estimate")
        START_AZIMUTH_FIELD_NUMBER: _ClassVar[int]
        START_RANGE_FIELD_NUMBER: _ClassVar[int]
        END_AZIMUTH_FIELD_NUMBER: _ClassVar[int]
        END_RANGE_FIELD_NUMBER: _ClassVar[int]
        ESTIMATE_FIELD_NUMBER: _ClassVar[int]
        start_azimuth: float
        start_range: int
        end_azimuth: float
        end_range: int
        estimate: int
        def __init__(self, start_azimuth: _Optional[float] = ..., start_range: _Optional[int] = ..., end_azimuth: _Optional[float] = ..., end_range: _Optional[int] = ..., estimate: _Optional[int] = ...) -> None: ...
    COMMON_FIELD_NUMBER: _ClassVar[int]
    IS_FULL_FIELD_NUMBER: _ClassVar[int]
    AIRPORT_FIELD_NUMBER: _ClassVar[int]
    SEQ_NUM_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    TRACK_FIELD_NUMBER: _ClassVar[int]
    STID_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_ID_FIELD_NUMBER: _ClassVar[int]
    ENHANCED_DATA_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_INFO_FIELD_NUMBER: _ClassVar[int]
    MANUAL_FIELD_NUMBER: _ClassVar[int]
    MOVEMENT_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    SLC_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TARGET_EXTENT_FIELD_NUMBER: _ClassVar[int]
    PLOT_COUNT_FIELD_NUMBER: _ClassVar[int]
    POSITION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    is_full: bool
    airport: str
    seq_num: int
    time: str
    track: int
    stid: int
    flight_id: PositionReport.FlightId
    enhanced_data: PositionReport.EnhancedData
    flight_info: PositionReport.FlightInfo
    manual: PositionReport.Manual
    movement: PositionReport.Movement
    position: PositionReport.Position
    slc: PositionReport.Slc
    status: PositionReport.Status
    target_extent: PositionReport.TargetExtent
    plot_count: int
    position_timestamp: int
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., is_full: _Optional[bool] = ..., airport: _Optional[str] = ..., seq_num: _Optional[int] = ..., time: _Optional[str] = ..., track: _Optional[int] = ..., stid: _Optional[int] = ..., flight_id: _Optional[_Union[PositionReport.FlightId, _Mapping]] = ..., enhanced_data: _Optional[_Union[PositionReport.EnhancedData, _Mapping]] = ..., flight_info: _Optional[_Union[PositionReport.FlightInfo, _Mapping]] = ..., manual: _Optional[_Union[PositionReport.Manual, _Mapping]] = ..., movement: _Optional[_Union[PositionReport.Movement, _Mapping]] = ..., position: _Optional[_Union[PositionReport.Position, _Mapping]] = ..., slc: _Optional[_Union[PositionReport.Slc, _Mapping]] = ..., status: _Optional[_Union[PositionReport.Status, _Mapping]] = ..., target_extent: _Optional[_Union[PositionReport.TargetExtent, _Mapping]] = ..., plot_count: _Optional[int] = ..., position_timestamp: _Optional[int] = ...) -> None: ...
