from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pymap3d

from .. import protos_path  # noqa: F401
from uni.protobuf.uni_track_schemas.fusion.v1beta.fusion_changed_event_pb2 import APPEND_ONLY, FusionChangedEvent
from uni_track_source_adsbx_plot_schema.proto.plot_pb2 import ADSBXPlotType
from ..raw_plots import RawPlot
from ..strategy import STATE_PREFIX, Record

FEET = 0.3048                 # metres per foot
KNOTS = 1.943844              # knots per metre per second
SOURCE_ID = {"adsbx": 4, "uavionix": 11}   # common.source_identifier per source name
ADSB_TYPES = {1, 2}           # ADSB_ICAO and ADSB_ICAO_NT: positions the aircraft broadcast itself
NACP_95_M = {11: 3, 10: 10, 9: 30, 8: 92.6, 7: 185.2, 6: 555.6, 5: 926, 4: 1852, 3: 3704, 2: 7408, 1: 18520}
H = np.hstack([np.eye(3), np.zeros((3, 3))])   # the measurement is the position part of the state

@dataclass
class Measurement:
    hex: str
    timestamp_s: float  # seconds
    lat: float
    lon: float
    altitude_m: float   # barometric altitude
    nacp: int | None

def accept(plot: RawPlot) -> Measurement | str:
    """ADS-B Exchange and uAvionix plots of an ADS-B position with a hex and an altitude, in the air.
    Anything else comes back as the reason it was skipped, a few words the viewer can show."""
    proto, common = plot.proto, plot.proto.common
    if plot.source == "adsbx":
        if proto.type not in ADSB_TYPES:
            return f"not an ADS-B position: ADS-B Exchange type is {ADSBXPlotType.Name(proto.type)}"
        if proto.alt_baro == "ground":
            return "on the ground"
        nacp = proto.nac_p if proto.HasField("nac_p") else None
    elif plot.source == "uavionix":
        if proto.target_report_descriptor.is_ground_bit_set:
            return "on the ground"
        nacp = proto.quality_indicators.nacp if proto.quality_indicators.HasField("nacp") else None
    else:
        return f"source not used: {plot.source}"
    if not common.adshex:
        return "no hex"
    if not common.HasField("altitude_ft"):
        return "no altitude"
    return Measurement(hex=common.adshex, timestamp_s=common.position_timestamp / 1e6, lat=common.latitude, lon=common.longitude,
                       altitude_m=common.altitude_ft * FEET, nacp=nacp)


@dataclass
class Track:
    hex: str
    timestamp_s: float  # seconds, position time of the last accepted plot
    x: np.ndarray       # state: x, y, z, vx, vy, vz in ECEF, metres and metres per second
    P: np.ndarray       # uncertainty of the state, 6 by 6


def start(m: Measurement, z: np.ndarray, R: np.ndarray, params: dict) -> Track:
    x = np.concatenate([z, np.zeros(3)])
    P = np.zeros((6, 6))
    P[:3, :3] = R
    P[3:, 3:] = np.eye(3) * params["start_velocity_sigma_mps"] ** 2
    return Track(hex=m.hex, timestamp_s=m.timestamp_s, x=x, P=P)


def predict(track: Track, dt: float, spectral_density: float) -> None:
    """Constant velocity for dt seconds: the position moves, the uncertainty grows."""
    F = np.eye(6)
    F[:3, 3:] = np.eye(3) * dt
    track.x = F @ track.x
    track.P = F @ track.P @ F.T + process_noise(dt, spectral_density)


def process_noise(dt: float, q: float) -> np.ndarray:
    """Q for a velocity that wanders like white noise with spectral density q, per axis."""
    Q = np.zeros((6, 6))
    for i in range(3):
        Q[i, i] = q * dt ** 3 / 3
        Q[i, i + 3] = Q[i + 3, i] = q * dt ** 2 / 2
        Q[i + 3, i + 3] = q * dt
    return Q


def measurement_noise(m: Measurement, params: dict) -> np.ndarray:
    """R: how far off this plot may be, as a 3 by 3 matrix in ECEF. NACp gives the 95% radius; half of
    it is the sigma east and north, up gets a bit more, and no NACp means the default."""
    radius = NACP_95_M.get(m.nacp or 0)
    sigma = radius / 2 if radius else params["default_sigma_m"]
    return enu_to_ecef(np.diag([sigma ** 2, sigma ** 2, (sigma * params["vertical_ratio"]) ** 2]), m.lat, m.lon)


def enu_to_ecef(matrix_enu: np.ndarray, lat: float, lon: float) -> np.ndarray:
    """Rotate a 3 by 3 matrix given in east, north, up at (lat, lon) into ECEF axes."""
    # columns are the east, north and up unit vectors written in ECEF, so rotation @ v_enu is v_ecef
    rotation = np.array(pymap3d.enu2uvw(np.eye(3)[0], np.eye(3)[1], np.eye(3)[2], lat, lon))
    return rotation @ matrix_enu @ rotation.T


def update(track: Track, z: np.ndarray, R: np.ndarray) -> tuple[float, float]:
    """Correct the state with a position measurement z of uncertainty R. Returns how far the plot was from
    where we expected it, in metres and in sigmas (below 3 in 97 of 100 plots if the noise is right; 10 is far off what we believed)."""
    innovation = z - H @ track.x                       # how far the plot is from where we expected it
    S = H @ track.P @ H.T + R                          # how far off that difference may be
    K = track.P @ H.T @ np.linalg.inv(S)               # how much of the difference to believe
    track.x = track.x + K @ innovation
    track.P = (np.eye(6) - K @ H) @ track.P
    return float(np.linalg.norm(innovation)), float(np.sqrt(innovation @ np.linalg.inv(S) @ innovation))


class Kalman:
    name = "kalman"
    params = dict(
        spectral_density=0.5,         # process noise: how much the velocity may wander, (m/s^2)^2 * s
        default_sigma_m=500.0,        # position sigma when the plot has no usable NACp
        vertical_ratio=1.5,           # up sigma = horizontal sigma * this
        start_velocity_sigma_mps=300.0,   # how unsure a new track is about its velocity
    )

    def __init__(self, record: Record, **overrides):
        self.record = record
        self.params = {**Kalman.params, **overrides}
        self.tracks: dict[str, Track] = {}

    def on_plot(self, plot: RawPlot) -> list[FusionChangedEvent]:
        measurement = accept(plot)
        if isinstance(measurement, str):
            self.record.skipped(measurement)
            return []
        z = np.array(pymap3d.geodetic2ecef(measurement.lat, measurement.lon, measurement.altitude_m))
        R = measurement_noise(measurement, self.params)

        # first plot of this aircraft: a new track that knows its position and nothing about its velocity
        track = self.tracks.get(measurement.hex)
        if track is None:
            track = self.tracks[measurement.hex] = start(measurement, z, R, self.params)
            self.record.used(track.hex)
            self.record.track(track.hex, **sigmas(track), **state_numbers(track))
            return [make_event(track, plot)]

        # an older or duplicate plot is dropped, the filter only moves forward in time
        if measurement.timestamp_s <= track.timestamp_s:
            self.record.dropped("duplicate" if measurement.timestamp_s == track.timestamp_s else "out of order", track.hex)
            return []

        # move the track to the plot's time, then pull it toward the plot
        predict(track, measurement.timestamp_s - track.timestamp_s, self.params["spectral_density"])
        distance_m, distance_sigmas = update(track, z, R)
        track.timestamp_s = measurement.timestamp_s
        self.record.used(track.hex, distance_m=distance_m, distance_sigmas=distance_sigmas)
        self.record.track(track.hex, **sigmas(track), **state_numbers(track))
        return [make_event(track, plot)]

    def finish(self) -> list[FusionChangedEvent]:
        return []

    @staticmethod
    def predict(state: dict[str, float], seconds: float, params: dict) -> dict:
        """Where the filter expects the aircraft `seconds` after one of its fused plots, by the same constant velocity
        step and process noise it runs on, from the state it recorded there."""
        track = from_state(state)
        predict(track, seconds, {**Kalman.params, **params}["spectral_density"])
        lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
        s = sigmas(track)
        return dict(latitude=float(lat), longitude=float(lon), sigma_east_m=s["sigma_east_m"], sigma_north_m=s["sigma_north_m"],
                    cov_east_north_m2=s["cov_east_north_m2"])


# the state x in ECEF, then P by its upper triangle, as named numbers for record.track
STATE_NAMES = ["x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps"]


def state_numbers(track: Track) -> dict[str, float]:
    out = {STATE_PREFIX + name: float(value) for name, value in zip(STATE_NAMES, track.x)}
    out.update({f"{STATE_PREFIX}p_{i}_{j}": float(track.P[i, j]) for i in range(6) for j in range(i, 6)})
    return out


def from_state(state: dict[str, float]) -> Track:
    P = np.zeros((6, 6))
    for i in range(6):
        for j in range(i, 6):
            P[i, j] = P[j, i] = state[f"{STATE_PREFIX}p_{i}_{j}"]
    return Track(hex="", timestamp_s=0.0, x=np.array([state[STATE_PREFIX + name] for name in STATE_NAMES]), P=P)


def sigmas(track: Track) -> dict[str, float]:
    """The filter's own sigmas at this moment: east, north, up in metres and horizontal speed in metres per second, and the
    east-north covariance in square metres, which with the two sigmas gives the horizontal uncertainty ellipse.
    P is in ECEF, so its position and velocity blocks are rotated into east, north, up at the track's position."""
    lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
    rotation = np.array(pymap3d.enu2uvw(np.eye(3)[0], np.eye(3)[1], np.eye(3)[2], lat, lon))
    position = rotation.T @ track.P[:3, :3] @ rotation
    velocity = rotation.T @ track.P[3:, 3:] @ rotation
    sigma = np.sqrt(np.diag(position)); sigma_velocity = np.sqrt(np.diag(velocity))
    return dict(sigma_east_m=float(sigma[0]), sigma_north_m=float(sigma[1]), sigma_up_m=float(sigma[2]),
                cov_east_north_m2=float(position[0, 1]), sigma_speed_mps=float(np.sqrt(np.mean(sigma_velocity[:2] ** 2))))


def make_event(track: Track, plot: RawPlot) -> FusionChangedEvent:
    """The corrected state as one fused plot, appended to the aircraft's track."""
    common = plot.proto.common
    lat, lon, altitude_m = pymap3d.ecef2geodetic(*track.x[:3])
    east, north, _ = pymap3d.uvw2enu(*track.x[3:], lat, lon)

    event = FusionChangedEvent(track_id=track.hex, created_at=plot.received_us, quality=APPEND_ONLY)
    segment = event.changed_segments.add(since=plot.position_us, until=plot.position_us)
    fused = segment.fused_track.plots.add()
    c = fused.common
    c.source_identifier = SOURCE_ID[plot.source]
    c.track_identifier = common.track_identifier
    c.position_timestamp, c.source_received_timestamp, c.asi_received_timestamp = common.position_timestamp, common.source_received_timestamp, common.asi_received_timestamp
    c.latitude, c.longitude, c.altitude_ft = float(lat), float(lon), int(round(altitude_m / FEET))
    c.ground_speed_kt = float(np.hypot(east, north) * KNOTS)
    c.track_deg = float(np.degrees(np.arctan2(east, north)) % 360)
    c.adshex, c.callsign, c.tail_number, c.squawk = common.adshex, common.callsign, common.tail_number, common.squawk
    return event
