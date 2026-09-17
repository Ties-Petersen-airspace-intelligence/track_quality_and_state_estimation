from uni_track_plot_schema.proto import plot_pb2 as _plot_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AsterixCat021(_message.Message):
    __slots__ = ("common", "position_timestamp", "aircraft_operational_status", "data_source_identification", "emitter_category", "target_report_descriptor", "mode_3_a_code", "time_message_reception_position", "time_message_reception_velocity", "time_of_report_transmission", "target_address", "quality_indicators", "position", "high_resolution_position", "geometric_height", "flight_level", "air_speed", "true_airspeed", "magnetic_heading", "barometric_vertical_rate", "geometric_vertical_rate", "airborne_ground_vector", "target_identification", "target_status", "mops_version")
    class EmitterCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        EMITTER_CATEGORY_UNSPECIFIED: _ClassVar[AsterixCat021.EmitterCategory]
        NO_CATEGORY_INFO: _ClassVar[AsterixCat021.EmitterCategory]
        LIGHT_AIRCRAFT: _ClassVar[AsterixCat021.EmitterCategory]
        SMALL_AIRCRAFT: _ClassVar[AsterixCat021.EmitterCategory]
        MEDIUM_AIRCRAFT: _ClassVar[AsterixCat021.EmitterCategory]
        HIGH_VORTEX_LARGE: _ClassVar[AsterixCat021.EmitterCategory]
        HEAVY_AIRCRAFT: _ClassVar[AsterixCat021.EmitterCategory]
        HIGHLY_MANOEUVRABLE: _ClassVar[AsterixCat021.EmitterCategory]
        ROTORCRAFT: _ClassVar[AsterixCat021.EmitterCategory]
        GLIDER_OR_SAILPLANE: _ClassVar[AsterixCat021.EmitterCategory]
        LIGHTER_THAN_AIR: _ClassVar[AsterixCat021.EmitterCategory]
        UNMANNED: _ClassVar[AsterixCat021.EmitterCategory]
        SPACE_OR_TRANSATMOSPHERIC: _ClassVar[AsterixCat021.EmitterCategory]
        ULTRALIGHT_OR_HANDGLIDER_OR_PARAGLIDER: _ClassVar[AsterixCat021.EmitterCategory]
        PARACHUTIST_OR_SKYDIVER: _ClassVar[AsterixCat021.EmitterCategory]
        SURFACE_EMERGENCY: _ClassVar[AsterixCat021.EmitterCategory]
        SURFACE_SERVICE: _ClassVar[AsterixCat021.EmitterCategory]
        FIXED_GROUND_OR_TETHERED_OBSTRUCTION: _ClassVar[AsterixCat021.EmitterCategory]
        CLUSTER_OBSTACLE: _ClassVar[AsterixCat021.EmitterCategory]
        LINE_OBSTACLE: _ClassVar[AsterixCat021.EmitterCategory]
    EMITTER_CATEGORY_UNSPECIFIED: AsterixCat021.EmitterCategory
    NO_CATEGORY_INFO: AsterixCat021.EmitterCategory
    LIGHT_AIRCRAFT: AsterixCat021.EmitterCategory
    SMALL_AIRCRAFT: AsterixCat021.EmitterCategory
    MEDIUM_AIRCRAFT: AsterixCat021.EmitterCategory
    HIGH_VORTEX_LARGE: AsterixCat021.EmitterCategory
    HEAVY_AIRCRAFT: AsterixCat021.EmitterCategory
    HIGHLY_MANOEUVRABLE: AsterixCat021.EmitterCategory
    ROTORCRAFT: AsterixCat021.EmitterCategory
    GLIDER_OR_SAILPLANE: AsterixCat021.EmitterCategory
    LIGHTER_THAN_AIR: AsterixCat021.EmitterCategory
    UNMANNED: AsterixCat021.EmitterCategory
    SPACE_OR_TRANSATMOSPHERIC: AsterixCat021.EmitterCategory
    ULTRALIGHT_OR_HANDGLIDER_OR_PARAGLIDER: AsterixCat021.EmitterCategory
    PARACHUTIST_OR_SKYDIVER: AsterixCat021.EmitterCategory
    SURFACE_EMERGENCY: AsterixCat021.EmitterCategory
    SURFACE_SERVICE: AsterixCat021.EmitterCategory
    FIXED_GROUND_OR_TETHERED_OBSTRUCTION: AsterixCat021.EmitterCategory
    CLUSTER_OBSTACLE: AsterixCat021.EmitterCategory
    LINE_OBSTACLE: AsterixCat021.EmitterCategory
    class AircraftOperationalStatus(_message.Message):
        __slots__ = ("is_tcas_resolution_advisory_active", "target_tc_report_capability", "is_capable_of_supporting_target_state_reports", "is_capable_of_generating_arv_reports", "is_cdti_operational", "is_tcas_not_operational", "has_single_antenna_only")
        class TargetTcReportCapability(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            TARGET_TC_REPORT_CAPABILITY_UNSPECIFIED: _ClassVar[AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability]
            NO_SUPPORT: _ClassVar[AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability]
            SUPPORT_FOR_TC_PLUS_ZERO_REPORTS_ONLY: _ClassVar[AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability]
            SUPPORT_FOR_MULTIPLE_TC_REPORTS: _ClassVar[AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability]
        TARGET_TC_REPORT_CAPABILITY_UNSPECIFIED: AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability
        NO_SUPPORT: AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability
        SUPPORT_FOR_TC_PLUS_ZERO_REPORTS_ONLY: AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability
        SUPPORT_FOR_MULTIPLE_TC_REPORTS: AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability
        IS_TCAS_RESOLUTION_ADVISORY_ACTIVE_FIELD_NUMBER: _ClassVar[int]
        TARGET_TC_REPORT_CAPABILITY_FIELD_NUMBER: _ClassVar[int]
        IS_CAPABLE_OF_SUPPORTING_TARGET_STATE_REPORTS_FIELD_NUMBER: _ClassVar[int]
        IS_CAPABLE_OF_GENERATING_ARV_REPORTS_FIELD_NUMBER: _ClassVar[int]
        IS_CDTI_OPERATIONAL_FIELD_NUMBER: _ClassVar[int]
        IS_TCAS_NOT_OPERATIONAL_FIELD_NUMBER: _ClassVar[int]
        HAS_SINGLE_ANTENNA_ONLY_FIELD_NUMBER: _ClassVar[int]
        is_tcas_resolution_advisory_active: bool
        target_tc_report_capability: AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability
        is_capable_of_supporting_target_state_reports: bool
        is_capable_of_generating_arv_reports: bool
        is_cdti_operational: bool
        is_tcas_not_operational: bool
        has_single_antenna_only: bool
        def __init__(self, is_tcas_resolution_advisory_active: _Optional[bool] = ..., target_tc_report_capability: _Optional[_Union[AsterixCat021.AircraftOperationalStatus.TargetTcReportCapability, str]] = ..., is_capable_of_supporting_target_state_reports: _Optional[bool] = ..., is_capable_of_generating_arv_reports: _Optional[bool] = ..., is_cdti_operational: _Optional[bool] = ..., is_tcas_not_operational: _Optional[bool] = ..., has_single_antenna_only: _Optional[bool] = ...) -> None: ...
    class DataSourceIdentification(_message.Message):
        __slots__ = ("system_area_code", "system_identification_code")
        SYSTEM_AREA_CODE_FIELD_NUMBER: _ClassVar[int]
        SYSTEM_IDENTIFICATION_CODE_FIELD_NUMBER: _ClassVar[int]
        system_area_code: int
        system_identification_code: int
        def __init__(self, system_area_code: _Optional[int] = ..., system_identification_code: _Optional[int] = ...) -> None: ...
    class TargetReportDescriptor(_message.Message):
        __slots__ = ("address_type", "altitude_reporting_capability", "did_range_check_pass", "is_report_from_field_monitor", "has_differential_correction", "is_ground_bit_set", "is_simulated_target", "is_test_target", "is_not_capable_to_provide_selected_altitude", "confidence_level", "is_target_suspect", "did_independent_position_check_fail", "is_nogo_bit_set", "did_cpr_validation_fail", "is_ldpj_detected", "did_range_check_fail", "total_bits_corrected", "maximum_bits_corrected")
        class AddressType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ADDRESS_TYPE_UNSPECIFIED: _ClassVar[AsterixCat021.TargetReportDescriptor.AddressType]
            ICAO: _ClassVar[AsterixCat021.TargetReportDescriptor.AddressType]
            DUPLICATE: _ClassVar[AsterixCat021.TargetReportDescriptor.AddressType]
            SURFACE_VEHICLE: _ClassVar[AsterixCat021.TargetReportDescriptor.AddressType]
            ANONYMOUS: _ClassVar[AsterixCat021.TargetReportDescriptor.AddressType]
        ADDRESS_TYPE_UNSPECIFIED: AsterixCat021.TargetReportDescriptor.AddressType
        ICAO: AsterixCat021.TargetReportDescriptor.AddressType
        DUPLICATE: AsterixCat021.TargetReportDescriptor.AddressType
        SURFACE_VEHICLE: AsterixCat021.TargetReportDescriptor.AddressType
        ANONYMOUS: AsterixCat021.TargetReportDescriptor.AddressType
        class AltitudeReportingCapability(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ALTITUDE_CAPABILITY_UNSPECIFIED: _ClassVar[AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability]
            FT_25: _ClassVar[AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability]
            FT_100: _ClassVar[AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability]
            UNKNOWN: _ClassVar[AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability]
            INVALID: _ClassVar[AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability]
        ALTITUDE_CAPABILITY_UNSPECIFIED: AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability
        FT_25: AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability
        FT_100: AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability
        UNKNOWN: AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability
        INVALID: AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability
        class ConfidenceLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            CONFIDENCE_LEVEL_UNSPECIFIED: _ClassVar[AsterixCat021.TargetReportDescriptor.ConfidenceLevel]
            REPORT_VALID: _ClassVar[AsterixCat021.TargetReportDescriptor.ConfidenceLevel]
            REPORT_SUSPECT: _ClassVar[AsterixCat021.TargetReportDescriptor.ConfidenceLevel]
            NO_INFORMATION: _ClassVar[AsterixCat021.TargetReportDescriptor.ConfidenceLevel]
        CONFIDENCE_LEVEL_UNSPECIFIED: AsterixCat021.TargetReportDescriptor.ConfidenceLevel
        REPORT_VALID: AsterixCat021.TargetReportDescriptor.ConfidenceLevel
        REPORT_SUSPECT: AsterixCat021.TargetReportDescriptor.ConfidenceLevel
        NO_INFORMATION: AsterixCat021.TargetReportDescriptor.ConfidenceLevel
        ADDRESS_TYPE_FIELD_NUMBER: _ClassVar[int]
        ALTITUDE_REPORTING_CAPABILITY_FIELD_NUMBER: _ClassVar[int]
        DID_RANGE_CHECK_PASS_FIELD_NUMBER: _ClassVar[int]
        IS_REPORT_FROM_FIELD_MONITOR_FIELD_NUMBER: _ClassVar[int]
        HAS_DIFFERENTIAL_CORRECTION_FIELD_NUMBER: _ClassVar[int]
        IS_GROUND_BIT_SET_FIELD_NUMBER: _ClassVar[int]
        IS_SIMULATED_TARGET_FIELD_NUMBER: _ClassVar[int]
        IS_TEST_TARGET_FIELD_NUMBER: _ClassVar[int]
        IS_NOT_CAPABLE_TO_PROVIDE_SELECTED_ALTITUDE_FIELD_NUMBER: _ClassVar[int]
        CONFIDENCE_LEVEL_FIELD_NUMBER: _ClassVar[int]
        IS_TARGET_SUSPECT_FIELD_NUMBER: _ClassVar[int]
        DID_INDEPENDENT_POSITION_CHECK_FAIL_FIELD_NUMBER: _ClassVar[int]
        IS_NOGO_BIT_SET_FIELD_NUMBER: _ClassVar[int]
        DID_CPR_VALIDATION_FAIL_FIELD_NUMBER: _ClassVar[int]
        IS_LDPJ_DETECTED_FIELD_NUMBER: _ClassVar[int]
        DID_RANGE_CHECK_FAIL_FIELD_NUMBER: _ClassVar[int]
        TOTAL_BITS_CORRECTED_FIELD_NUMBER: _ClassVar[int]
        MAXIMUM_BITS_CORRECTED_FIELD_NUMBER: _ClassVar[int]
        address_type: AsterixCat021.TargetReportDescriptor.AddressType
        altitude_reporting_capability: AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability
        did_range_check_pass: bool
        is_report_from_field_monitor: bool
        has_differential_correction: bool
        is_ground_bit_set: bool
        is_simulated_target: bool
        is_test_target: bool
        is_not_capable_to_provide_selected_altitude: bool
        confidence_level: AsterixCat021.TargetReportDescriptor.ConfidenceLevel
        is_target_suspect: bool
        did_independent_position_check_fail: bool
        is_nogo_bit_set: bool
        did_cpr_validation_fail: bool
        is_ldpj_detected: bool
        did_range_check_fail: bool
        total_bits_corrected: int
        maximum_bits_corrected: int
        def __init__(self, address_type: _Optional[_Union[AsterixCat021.TargetReportDescriptor.AddressType, str]] = ..., altitude_reporting_capability: _Optional[_Union[AsterixCat021.TargetReportDescriptor.AltitudeReportingCapability, str]] = ..., did_range_check_pass: _Optional[bool] = ..., is_report_from_field_monitor: _Optional[bool] = ..., has_differential_correction: _Optional[bool] = ..., is_ground_bit_set: _Optional[bool] = ..., is_simulated_target: _Optional[bool] = ..., is_test_target: _Optional[bool] = ..., is_not_capable_to_provide_selected_altitude: _Optional[bool] = ..., confidence_level: _Optional[_Union[AsterixCat021.TargetReportDescriptor.ConfidenceLevel, str]] = ..., is_target_suspect: _Optional[bool] = ..., did_independent_position_check_fail: _Optional[bool] = ..., is_nogo_bit_set: _Optional[bool] = ..., did_cpr_validation_fail: _Optional[bool] = ..., is_ldpj_detected: _Optional[bool] = ..., did_range_check_fail: _Optional[bool] = ..., total_bits_corrected: _Optional[int] = ..., maximum_bits_corrected: _Optional[int] = ...) -> None: ...
    class QualityIndicators(_message.Message):
        __slots__ = ("nucr_or_nacv", "nucp_or_nic", "nic_baro", "sil", "nacp", "is_sil_measured_per_sample", "system_design_assurance", "geometric_vertical_accuracy", "position_integrity_category")
        NUCR_OR_NACV_FIELD_NUMBER: _ClassVar[int]
        NUCP_OR_NIC_FIELD_NUMBER: _ClassVar[int]
        NIC_BARO_FIELD_NUMBER: _ClassVar[int]
        SIL_FIELD_NUMBER: _ClassVar[int]
        NACP_FIELD_NUMBER: _ClassVar[int]
        IS_SIL_MEASURED_PER_SAMPLE_FIELD_NUMBER: _ClassVar[int]
        SYSTEM_DESIGN_ASSURANCE_FIELD_NUMBER: _ClassVar[int]
        GEOMETRIC_VERTICAL_ACCURACY_FIELD_NUMBER: _ClassVar[int]
        POSITION_INTEGRITY_CATEGORY_FIELD_NUMBER: _ClassVar[int]
        nucr_or_nacv: int
        nucp_or_nic: int
        nic_baro: int
        sil: int
        nacp: int
        is_sil_measured_per_sample: bool
        system_design_assurance: int
        geometric_vertical_accuracy: int
        position_integrity_category: int
        def __init__(self, nucr_or_nacv: _Optional[int] = ..., nucp_or_nic: _Optional[int] = ..., nic_baro: _Optional[int] = ..., sil: _Optional[int] = ..., nacp: _Optional[int] = ..., is_sil_measured_per_sample: _Optional[bool] = ..., system_design_assurance: _Optional[int] = ..., geometric_vertical_accuracy: _Optional[int] = ..., position_integrity_category: _Optional[int] = ...) -> None: ...
    class Position(_message.Message):
        __slots__ = ("latitude", "longitude")
        LATITUDE_FIELD_NUMBER: _ClassVar[int]
        LONGITUDE_FIELD_NUMBER: _ClassVar[int]
        latitude: float
        longitude: float
        def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...
    class HighResolutionPosition(_message.Message):
        __slots__ = ("latitude", "longitude")
        LATITUDE_FIELD_NUMBER: _ClassVar[int]
        LONGITUDE_FIELD_NUMBER: _ClassVar[int]
        latitude: float
        longitude: float
        def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...
    class AirSpeed(_message.Message):
        __slots__ = ("is_mach", "air_speed")
        IS_MACH_FIELD_NUMBER: _ClassVar[int]
        AIR_SPEED_FIELD_NUMBER: _ClassVar[int]
        is_mach: bool
        air_speed: float
        def __init__(self, is_mach: _Optional[bool] = ..., air_speed: _Optional[float] = ...) -> None: ...
    class TrueAirspeed(_message.Message):
        __slots__ = ("is_range_exceeded", "true_airspeed")
        IS_RANGE_EXCEEDED_FIELD_NUMBER: _ClassVar[int]
        TRUE_AIRSPEED_FIELD_NUMBER: _ClassVar[int]
        is_range_exceeded: bool
        true_airspeed: float
        def __init__(self, is_range_exceeded: _Optional[bool] = ..., true_airspeed: _Optional[float] = ...) -> None: ...
    class AirborneGroundVector(_message.Message):
        __slots__ = ("is_range_exceeded", "ground_speed", "track_angle")
        IS_RANGE_EXCEEDED_FIELD_NUMBER: _ClassVar[int]
        GROUND_SPEED_FIELD_NUMBER: _ClassVar[int]
        TRACK_ANGLE_FIELD_NUMBER: _ClassVar[int]
        is_range_exceeded: bool
        ground_speed: float
        track_angle: float
        def __init__(self, is_range_exceeded: _Optional[bool] = ..., ground_speed: _Optional[float] = ..., track_angle: _Optional[float] = ...) -> None: ...
    class TargetStatus(_message.Message):
        __slots__ = ("is_intent_change_active", "is_not_lateral_navigation_engaged", "is_military_emergency", "priority_status", "surveillance_status")
        class PriorityStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            PRIORITY_STATUS_UNSPECIFIED: _ClassVar[AsterixCat021.TargetStatus.PriorityStatus]
            GENERAL_EMERGENCY: _ClassVar[AsterixCat021.TargetStatus.PriorityStatus]
            LIFEGUARD_MEDICAL_EMERGENCY: _ClassVar[AsterixCat021.TargetStatus.PriorityStatus]
            MINIMUM_FUEL: _ClassVar[AsterixCat021.TargetStatus.PriorityStatus]
            NO_COMMUNICATIONS: _ClassVar[AsterixCat021.TargetStatus.PriorityStatus]
            UNLAWFUL_INTERFERENCE: _ClassVar[AsterixCat021.TargetStatus.PriorityStatus]
            DOWNED_AIRCRAFT: _ClassVar[AsterixCat021.TargetStatus.PriorityStatus]
        PRIORITY_STATUS_UNSPECIFIED: AsterixCat021.TargetStatus.PriorityStatus
        GENERAL_EMERGENCY: AsterixCat021.TargetStatus.PriorityStatus
        LIFEGUARD_MEDICAL_EMERGENCY: AsterixCat021.TargetStatus.PriorityStatus
        MINIMUM_FUEL: AsterixCat021.TargetStatus.PriorityStatus
        NO_COMMUNICATIONS: AsterixCat021.TargetStatus.PriorityStatus
        UNLAWFUL_INTERFERENCE: AsterixCat021.TargetStatus.PriorityStatus
        DOWNED_AIRCRAFT: AsterixCat021.TargetStatus.PriorityStatus
        class SurveillanceStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            SURVEILLANCE_STATUS_UNSPECIFIED: _ClassVar[AsterixCat021.TargetStatus.SurveillanceStatus]
            PERMANENT_ALERT: _ClassVar[AsterixCat021.TargetStatus.SurveillanceStatus]
            TEMPORARY_ALERT: _ClassVar[AsterixCat021.TargetStatus.SurveillanceStatus]
            SPI_SET: _ClassVar[AsterixCat021.TargetStatus.SurveillanceStatus]
        SURVEILLANCE_STATUS_UNSPECIFIED: AsterixCat021.TargetStatus.SurveillanceStatus
        PERMANENT_ALERT: AsterixCat021.TargetStatus.SurveillanceStatus
        TEMPORARY_ALERT: AsterixCat021.TargetStatus.SurveillanceStatus
        SPI_SET: AsterixCat021.TargetStatus.SurveillanceStatus
        IS_INTENT_CHANGE_ACTIVE_FIELD_NUMBER: _ClassVar[int]
        IS_NOT_LATERAL_NAVIGATION_ENGAGED_FIELD_NUMBER: _ClassVar[int]
        IS_MILITARY_EMERGENCY_FIELD_NUMBER: _ClassVar[int]
        PRIORITY_STATUS_FIELD_NUMBER: _ClassVar[int]
        SURVEILLANCE_STATUS_FIELD_NUMBER: _ClassVar[int]
        is_intent_change_active: bool
        is_not_lateral_navigation_engaged: bool
        is_military_emergency: bool
        priority_status: AsterixCat021.TargetStatus.PriorityStatus
        surveillance_status: AsterixCat021.TargetStatus.SurveillanceStatus
        def __init__(self, is_intent_change_active: _Optional[bool] = ..., is_not_lateral_navigation_engaged: _Optional[bool] = ..., is_military_emergency: _Optional[bool] = ..., priority_status: _Optional[_Union[AsterixCat021.TargetStatus.PriorityStatus, str]] = ..., surveillance_status: _Optional[_Union[AsterixCat021.TargetStatus.SurveillanceStatus, str]] = ...) -> None: ...
    class MOPS(_message.Message):
        __slots__ = ("is_mops_version_not_supported", "mops_version", "link_technology")
        class MopsVersion(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            MOPS_VERSION_UNSPECIFIED: _ClassVar[AsterixCat021.MOPS.MopsVersion]
            DO_260: _ClassVar[AsterixCat021.MOPS.MopsVersion]
            DO_260A: _ClassVar[AsterixCat021.MOPS.MopsVersion]
            DO_260B: _ClassVar[AsterixCat021.MOPS.MopsVersion]
            DO_260C: _ClassVar[AsterixCat021.MOPS.MopsVersion]
        MOPS_VERSION_UNSPECIFIED: AsterixCat021.MOPS.MopsVersion
        DO_260: AsterixCat021.MOPS.MopsVersion
        DO_260A: AsterixCat021.MOPS.MopsVersion
        DO_260B: AsterixCat021.MOPS.MopsVersion
        DO_260C: AsterixCat021.MOPS.MopsVersion
        class LinkTechnologyType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            LINK_TECHNOLOGY_TYPE_UNSPECIFIED: _ClassVar[AsterixCat021.MOPS.LinkTechnologyType]
            OTHER: _ClassVar[AsterixCat021.MOPS.LinkTechnologyType]
            UAT: _ClassVar[AsterixCat021.MOPS.LinkTechnologyType]
            ES_1090: _ClassVar[AsterixCat021.MOPS.LinkTechnologyType]
            VDL_4: _ClassVar[AsterixCat021.MOPS.LinkTechnologyType]
        LINK_TECHNOLOGY_TYPE_UNSPECIFIED: AsterixCat021.MOPS.LinkTechnologyType
        OTHER: AsterixCat021.MOPS.LinkTechnologyType
        UAT: AsterixCat021.MOPS.LinkTechnologyType
        ES_1090: AsterixCat021.MOPS.LinkTechnologyType
        VDL_4: AsterixCat021.MOPS.LinkTechnologyType
        IS_MOPS_VERSION_NOT_SUPPORTED_FIELD_NUMBER: _ClassVar[int]
        MOPS_VERSION_FIELD_NUMBER: _ClassVar[int]
        LINK_TECHNOLOGY_FIELD_NUMBER: _ClassVar[int]
        is_mops_version_not_supported: bool
        mops_version: AsterixCat021.MOPS.MopsVersion
        link_technology: AsterixCat021.MOPS.LinkTechnologyType
        def __init__(self, is_mops_version_not_supported: _Optional[bool] = ..., mops_version: _Optional[_Union[AsterixCat021.MOPS.MopsVersion, str]] = ..., link_technology: _Optional[_Union[AsterixCat021.MOPS.LinkTechnologyType, str]] = ...) -> None: ...
    COMMON_FIELD_NUMBER: _ClassVar[int]
    POSITION_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    AIRCRAFT_OPERATIONAL_STATUS_FIELD_NUMBER: _ClassVar[int]
    DATA_SOURCE_IDENTIFICATION_FIELD_NUMBER: _ClassVar[int]
    EMITTER_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TARGET_REPORT_DESCRIPTOR_FIELD_NUMBER: _ClassVar[int]
    MODE_3_A_CODE_FIELD_NUMBER: _ClassVar[int]
    TIME_MESSAGE_RECEPTION_POSITION_FIELD_NUMBER: _ClassVar[int]
    TIME_MESSAGE_RECEPTION_VELOCITY_FIELD_NUMBER: _ClassVar[int]
    TIME_OF_REPORT_TRANSMISSION_FIELD_NUMBER: _ClassVar[int]
    TARGET_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    QUALITY_INDICATORS_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    HIGH_RESOLUTION_POSITION_FIELD_NUMBER: _ClassVar[int]
    GEOMETRIC_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    FLIGHT_LEVEL_FIELD_NUMBER: _ClassVar[int]
    AIR_SPEED_FIELD_NUMBER: _ClassVar[int]
    TRUE_AIRSPEED_FIELD_NUMBER: _ClassVar[int]
    MAGNETIC_HEADING_FIELD_NUMBER: _ClassVar[int]
    BAROMETRIC_VERTICAL_RATE_FIELD_NUMBER: _ClassVar[int]
    GEOMETRIC_VERTICAL_RATE_FIELD_NUMBER: _ClassVar[int]
    AIRBORNE_GROUND_VECTOR_FIELD_NUMBER: _ClassVar[int]
    TARGET_IDENTIFICATION_FIELD_NUMBER: _ClassVar[int]
    TARGET_STATUS_FIELD_NUMBER: _ClassVar[int]
    MOPS_VERSION_FIELD_NUMBER: _ClassVar[int]
    common: _plot_pb2.Common
    position_timestamp: int
    aircraft_operational_status: AsterixCat021.AircraftOperationalStatus
    data_source_identification: AsterixCat021.DataSourceIdentification
    emitter_category: AsterixCat021.EmitterCategory
    target_report_descriptor: AsterixCat021.TargetReportDescriptor
    mode_3_a_code: int
    time_message_reception_position: float
    time_message_reception_velocity: float
    time_of_report_transmission: float
    target_address: int
    quality_indicators: AsterixCat021.QualityIndicators
    position: AsterixCat021.Position
    high_resolution_position: AsterixCat021.HighResolutionPosition
    geometric_height: float
    flight_level: float
    air_speed: AsterixCat021.AirSpeed
    true_airspeed: AsterixCat021.TrueAirspeed
    magnetic_heading: float
    barometric_vertical_rate: float
    geometric_vertical_rate: float
    airborne_ground_vector: AsterixCat021.AirborneGroundVector
    target_identification: str
    target_status: AsterixCat021.TargetStatus
    mops_version: AsterixCat021.MOPS
    def __init__(self, common: _Optional[_Union[_plot_pb2.Common, _Mapping]] = ..., position_timestamp: _Optional[int] = ..., aircraft_operational_status: _Optional[_Union[AsterixCat021.AircraftOperationalStatus, _Mapping]] = ..., data_source_identification: _Optional[_Union[AsterixCat021.DataSourceIdentification, _Mapping]] = ..., emitter_category: _Optional[_Union[AsterixCat021.EmitterCategory, str]] = ..., target_report_descriptor: _Optional[_Union[AsterixCat021.TargetReportDescriptor, _Mapping]] = ..., mode_3_a_code: _Optional[int] = ..., time_message_reception_position: _Optional[float] = ..., time_message_reception_velocity: _Optional[float] = ..., time_of_report_transmission: _Optional[float] = ..., target_address: _Optional[int] = ..., quality_indicators: _Optional[_Union[AsterixCat021.QualityIndicators, _Mapping]] = ..., position: _Optional[_Union[AsterixCat021.Position, _Mapping]] = ..., high_resolution_position: _Optional[_Union[AsterixCat021.HighResolutionPosition, _Mapping]] = ..., geometric_height: _Optional[float] = ..., flight_level: _Optional[float] = ..., air_speed: _Optional[_Union[AsterixCat021.AirSpeed, _Mapping]] = ..., true_airspeed: _Optional[_Union[AsterixCat021.TrueAirspeed, _Mapping]] = ..., magnetic_heading: _Optional[float] = ..., barometric_vertical_rate: _Optional[float] = ..., geometric_vertical_rate: _Optional[float] = ..., airborne_ground_vector: _Optional[_Union[AsterixCat021.AirborneGroundVector, _Mapping]] = ..., target_identification: _Optional[str] = ..., target_status: _Optional[_Union[AsterixCat021.TargetStatus, _Mapping]] = ..., mops_version: _Optional[_Union[AsterixCat021.MOPS, _Mapping]] = ...) -> None: ...
