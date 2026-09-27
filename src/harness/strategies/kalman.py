from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pymap3d

from ..normalization.measurement import Measurement
from ..strategy import STATE_PREFIX, StrategyResult, TrackPoint, TrackUpdate

FEET = 0.3048                 # metres per foot
KNOTS = 1.943844              # knots per metre per second
KINDS = {"own_gps", "mlat"}   # the aircraft's own GPS position, and MLAT: a position worked out on the ground from arrival times
RADIUS_95_IN_SIGMAS = 2.45    # a circle of this many sigmas holds 95% of positions spread evenly in east and north
H = np.hstack([np.eye(3), np.zeros((3, 3))])   # the measurement is the position part of the state


def skip_reason(m: Measurement) -> str:
    """Why a measurement is not for this filter, a few words the viewer can show, or "" when it is: it takes own GPS and MLAT
    plots in the air with a hex and an altitude."""
    if m.kind not in KINDS:
        return f"kind not used: {m.kind}"
    if m.is_on_ground:
        return "on the ground"
    if not m.hex:
        return "no hex"
    if m.altitude_ft is None:
        return "no altitude"
    return ""


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
    return Track(hex=m.hex, timestamp_s=m.position_us / 1e6, x=x, P=P)


def predict(track: Track, dt: float, params: dict, lat: float | None = None, lon: float | None = None) -> None:
    """Constant velocity for dt seconds: the position moves, the uncertainty grows. The process noise is set in east, north
    and up at (lat, lon), the track's own position when not given."""
    if lat is None or lon is None:
        lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
    F = np.eye(6)
    F[:3, 3:] = np.eye(3) * dt
    track.x = F @ track.x
    track.P = F @ track.P @ F.T + process_noise(dt, params, lat, lon)


def process_noise(dt: float, params: dict, lat: float, lon: float) -> np.ndarray:
    """Q for a velocity that wanders like white noise, with one spectral density east and north and a smaller one up,
    rotated from east, north, up at (lat, lon) into ECEF."""
    q = np.diag([params["spectral_density_horizontal"]] * 2 + [params["spectral_density_vertical"]])
    Q = np.zeros((6, 6))
    Q[:3, :3] = enu_to_ecef(q * dt ** 3 / 3, lat, lon)
    Q[:3, 3:] = Q[3:, :3] = enu_to_ecef(q * dt ** 2 / 2, lat, lon)
    Q[3:, 3:] = enu_to_ecef(q * dt, lat, lon)
    return Q


def measurement_sigma_m(m: Measurement) -> float:
    """How far off this plot may be east and north, one sigma in metres: the normalizer's 95% radius, which for a round spread in the
    plane is 2.45 sigma."""
    return m.accuracy_95_m / RADIUS_95_IN_SIGMAS


def measurement_noise(sigma: float, m: Measurement, params: dict) -> np.ndarray:
    """R: the plot's sigma east and north, up a bit more, as a 3 by 3 matrix in ECEF."""
    return enu_to_ecef(np.diag([sigma ** 2, sigma ** 2, (sigma * params["vertical_ratio"]) ** 2]), m.lat, m.lon)


def enu_to_ecef(matrix_enu: np.ndarray, lat: float, lon: float) -> np.ndarray:
    """Rotate a 3 by 3 matrix given in east, north, up at (lat, lon) into ECEF axes."""
    # columns are the east, north and up unit vectors written in ECEF, so rotation @ v_enu is v_ecef
    rotation = np.array(pymap3d.enu2uvw(np.eye(3)[0], np.eye(3)[1], np.eye(3)[2], lat, lon))
    return rotation @ matrix_enu @ rotation.T


def correct(track: Track, z: np.ndarray, R: np.ndarray) -> tuple[float, float]:
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
        spectral_density_horizontal=1.0,   # process noise east and north: how much the velocity may wander, (m/s^2)^2 * s;
                                           # fits the median 60 s miss of a straight-line guess for aircraft under 195 kt
        spectral_density_vertical=0.02,    # process noise up; altitude strays far less, median 20 m in 60 s
        vertical_ratio=1.5,           # up sigma = horizontal sigma * this
        start_velocity_sigma_mps=300.0,   # how unsure a new track is about its velocity
    )

    def __init__(self, **overrides):
        self.params = {**Kalman.params, **overrides}
        self.tracks: dict[str, Track] = {}

    def update(self, m: Measurement) -> StrategyResult:
        reason = skip_reason(m)
        if reason:
            return StrategyResult.skipped(reason)

        z = np.array(pymap3d.geodetic2ecef(m.lat, m.lon, m.altitude_ft * FEET))
        sigma = measurement_sigma_m(m)
        R = measurement_noise(sigma, m, self.params)

        # first plot of this aircraft: a new track that knows its position and nothing about its velocity
        track = self.tracks.get(m.hex)
        if track is None:
            track = self.tracks[m.hex] = start(m, z, R, self.params)
            return StrategyResult.used(track_update(track, m), measurement_sigma_m=sigma)

        # an older plot, or one at the same position time as the last used plot, is rejected: the filter only moves forward in time
        timestamp_s = m.position_us / 1e6
        if timestamp_s <= track.timestamp_s:
            return StrategyResult.rejected(track.hex, "same position time as the last used plot" if timestamp_s == track.timestamp_s else "out of order")

        # move the track to the plot's time, then pull it toward the plot
        predict(track, timestamp_s - track.timestamp_s, self.params, m.lat, m.lon)
        distance_m, distance_sigmas = correct(track, z, R)
        track.timestamp_s = timestamp_s
        return StrategyResult.used(track_update(track, m), distance_m=distance_m, distance_sigmas=distance_sigmas, measurement_sigma_m=sigma)

    @staticmethod
    def predict(state: dict[str, float], seconds: float, params: dict) -> dict:
        """Where the filter expects the aircraft `seconds` after one of its fused plots, by the same constant velocity
        step and process noise it runs on, from the state it recorded there."""
        track = from_state(state)
        predict(track, seconds, {**Kalman.params, **params})
        lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
        s = sigmas(track)
        return dict(latitude=float(lat), longitude=float(lon), sigma_east_m=s["sigma_east_m"], sigma_north_m=s["sigma_north_m"],
                    cov_east_north_m2=s["cov_east_north_m2"])


# the state x in ECEF, then P by its upper triangle, as named numbers of a track point
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


def track_update(track: Track, m: Measurement) -> TrackUpdate:
    """The corrected state as one point appended to the aircraft's track, with the filter's sigmas and its state for predict()."""
    lat, lon, altitude_m = pymap3d.ecef2geodetic(*track.x[:3])
    east, north, _ = pymap3d.uvw2enu(*track.x[3:], lat, lon)
    point = TrackPoint(position_us=m.position_us, source_received_us=m.source_received_us, received_us=m.received_us,
                       lat=float(lat), lon=float(lon), altitude_ft=int(round(altitude_m / FEET)),
                       ground_speed_kt=float(np.hypot(east, north) * KNOTS), track_deg=float(np.degrees(np.arctan2(east, north)) % 360),
                       hex=m.hex, callsign=m.callsign, tail=m.tail, squawk=m.squawk, track_identifier=m.track_identifier,
                       source_identifier=m.source_identifier, numbers={**sigmas(track), **state_numbers(track)})
    return TrackUpdate.append(track.hex, point)
