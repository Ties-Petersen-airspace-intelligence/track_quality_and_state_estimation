"""The basic normalizer: all the source knowledge the strategies need, in one place.

It removes plots that hold no position of their own: ADS-B Exchange MODE_S, an old position filled in next to a Mode S reply,
and ADS-B Exchange type UNKNOWN. Every other raw plot becomes a Measurement: the common fields under plain names, and three
things only the source's own fields tell:
- kind: own_gps for the aircraft's own GPS position (ADS-B Exchange ADS-B and ADS-R with an ICAO address, uAvionix, PlaneFinder
  ADS-B, Aireon); mlat for ADS-B Exchange MLAT; radar for TFMS Track Information and STDDS; report for TFMS oceanic reports, United and
  Alaska; a plain label of its own for everything else
- is_on_ground, for the sources that say: ADS-B Exchange, uAvionix, PlaneFinder and Aireon (where it sends the ground bit)
- track_deg from the source's own field where the common block leaves it empty: ADS-B Exchange `track`, PlaneFinder `track_angle`
- hex: the identity, empty for values that cannot identify one aircraft (000000, 000001, FFFFFF, too short)
- accuracy_95_m: own GPS with a NACp of 1 to 11 the NACp's radius; own GPS without a usable NACp (none, as in most ADS-R and
  all PlaneFinder and Aireon, or 0, as in every plot of an old version 0 transponder) and MLAT a default from params; other kinds none
- time_sigma_s: how far off the source's position times are, from params, per source; none for sources not measured yet
"""
from __future__ import annotations

from .. import protos_path  # noqa: F401
from uni_track_source_adsbx_plot_schema.proto.plot_pb2 import ADSBXPlotType as T
from uni_track_source_planefinder_plot_schema.proto.plot_pb2 import DataSource as D
from ..raw_plots import RawPlot
from .measurement import Measurement, NormalizationResult

# ADS-B Exchange type -> kind; types missing here are removed
ADSBX_KIND = {T.ADSB_ICAO: "own_gps", T.ADSB_ICAO_NT: "own_gps", T.ADSR_ICAO: "own_gps", T.MLAT: "mlat",
              T.TISB_ICAO: "tisb", T.TISB_TRACKFILE: "tisb", T.TISB_OTHER: "tisb", T.ADSC: "adsc",
              T.ADSB_OTHER: "adsb_other", T.ADSR_OTHER: "adsr_other", T.OTHER: "adsbx_other"}   # *_OTHER: no ICAO address
PLANEFINDER_KIND = {D.ADSB: "own_gps", D.PLANE_FINDER_MLAT: "planefinder_mlat", D.THIRD_PARTY_DERIVED_MLAT: "third_party_mlat",
                    D.FLARM: "flarm", D.BLOCKED_DATA: "planefinder_blocked", D.UNKNOWN: "planefinder_unknown"}
SOURCE_KIND = {"uavionix": "own_gps", "aireon": "own_gps", "tfms_ti": "radar", "stdds": "radar", "tfms_or": "report", "ual": "report", "asa": "report"}
NACP_95_M = {11: 3, 10: 10, 9: 30, 8: 92.6, 7: 185.2, 6: 555.6, 5: 926, 4: 1852, 3: 3704, 2: 7408, 1: 18520}


def identity_hex(hex: str) -> str:
    """The hex as an identity, or "" when it cannot be one: all zeros, all ones or shorter than six characters. A day of ADS-B
    Exchange showed 000001 carrying many aircraft at once."""
    h = hex.strip().upper()
    if len(h) < 6 or set(h) <= {"0"} or set(h) <= {"F"} or h == "000001":
        return ""
    return h


class Basic:
    name = "basic"
    params = dict(
        own_gps_no_nacp_accuracy_95_m=36.75,  # own GPS without a usable NACp: 15 m sigma east and north, times 2.45
        mlat_accuracy_95_m=1102.5,            # ADS-B Exchange MLAT: 450 m sigma times 2.45. Against a straight line over one minute its plots
                                              # stray a median 42 m and 95% under 400 m (a 150 m sigma), but MLAT is trusted too much in the
                                              # tracker (Ties, 28 Sep): its errors come in bursts of kilometres that a 150 m sigma lets through
        # how far off a source's position time may be, one sigma in seconds, measured as the miss along the direction of flight
        # divided by speed (experiment loop, iteration 1): uAvionix stamps the time of day to 1/128 s; ADS-B Exchange works the time
        # out from a poll clock and a "seen" age that drifts; PlaneFinder writes whole seconds and its stations disagree by up to 0.5 s
        uavionix_time_sigma_s=0.05,
        adsbx_time_sigma_s=0.15,
        planefinder_time_sigma_s=0.6,
    )

    def __init__(self, **overrides):
        self.params = {**Basic.params, **overrides}

    def normalize(self, plot: RawPlot) -> NormalizationResult:
        proto, common = plot.proto, plot.proto.common
        is_on_ground = nacp = vertical_rate = track_deg = None
        if plot.source == "adsbx":
            if proto.type not in ADSBX_KIND:
                return NormalizationResult.removed(f"adsbx type removed: {T.Name(proto.type)}")
            kind = ADSBX_KIND[proto.type]
            is_on_ground = proto.alt_baro == "ground"
            nacp = proto.nac_p if proto.HasField("nac_p") else None
            vertical_rate = proto.baro_rate if proto.HasField("baro_rate") else None
            track_deg = proto.track if proto.HasField("track") else None
        elif plot.source == "uavionix":
            kind = SOURCE_KIND[plot.source]
            is_on_ground = bool(proto.target_report_descriptor.is_ground_bit_set)
            nacp = proto.quality_indicators.nacp if proto.quality_indicators.HasField("nacp") else None
            vertical_rate = proto.barometric_vertical_rate if proto.HasField("barometric_vertical_rate") else None
        elif plot.source == "planefinder":
            kind = PLANEFINDER_KIND[proto.data_source]
            is_on_ground = bool(proto.is_on_ground)
            vertical_rate = float(proto.vert_rate) if proto.HasField("vert_rate") else None
            track_deg = float(proto.track_angle) if proto.HasField("track_angle") else None
        elif plot.source == "aireon":
            kind = SOURCE_KIND[plot.source]
            is_on_ground = proto.is_on_ground if proto.HasField("is_on_ground") else None
            # Aireon sends one of the two rates
            if proto.HasField("barometric_vertical_rate_ft_per_min"):
                vertical_rate = proto.barometric_vertical_rate_ft_per_min
            elif proto.HasField("geometric_vertical_rate_ft_per_min"):
                vertical_rate = proto.geometric_vertical_rate_ft_per_min
        else:
            kind = SOURCE_KIND[plot.source]

        optional = lambda name: getattr(common, name) if common.HasField(name) else None
        return NormalizationResult.kept(Measurement(
            source=plot.source, row=plot.row,
            position_us=common.position_timestamp, received_us=common.asi_received_timestamp, source_received_us=common.source_received_timestamp,
            lat=common.latitude, lon=common.longitude, altitude_ft=optional("altitude_ft"), is_on_ground=is_on_ground, kind=kind,
            accuracy_95_m=self.accuracy_95_m(kind, nacp), time_sigma_s=self.params.get(f"{plot.source}_time_sigma_s"),
            hex=identity_hex(common.adshex), callsign=common.callsign, tail=common.tail_number, squawk=common.squawk,
            track_identifier=common.track_identifier, flight_number=common.flight_number, source_identifier=common.source_identifier,
            ground_speed_kt=optional("ground_speed_kt"), track_deg=optional("track_deg") if track_deg is None else track_deg, heading_deg=optional("heading_deg"),
            vertical_rate_fpm=vertical_rate,
        ))

    def accuracy_95_m(self, kind: str, nacp: int | None) -> float | None:
        if kind == "mlat":
            return self.params["mlat_accuracy_95_m"]
        if kind == "own_gps":
            return NACP_95_M.get(nacp) or self.params["own_gps_no_nacp_accuracy_95_m"]
        return None
