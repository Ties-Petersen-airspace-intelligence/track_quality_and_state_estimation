from __future__ import annotations

from dataclasses import dataclass, field

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


@dataclass(eq=False)   # tracks are compared by identity, never by their arrays
class Track:
    hex: str
    timestamp_s: float  # seconds, position time of the last used plot
    x: np.ndarray       # state: x, y, z, vx, vy, vz in ECEF, metres and metres per second
    P: np.ndarray       # uncertainty of the state, 6 by 6
    id: str = ""        # hex:n, n counting the tracks born for this hex
    born_s: float = 0.0                                   # position time of the first plot
    points: list[TrackPoint] = field(default_factory=list)  # a candidate's points, published together when it is confirmed
    confirmed: bool = False


def start(m: Measurement, z: np.ndarray, R: np.ndarray, params: dict) -> Track:
    """A new track at the plot's position, moving as the plot reports (ground speed, track angle, vertical rate); a plot that
    reports no speed gives a track that knows nothing about its velocity."""
    velocity = reported_velocity(m)
    sigma = params["reported_velocity_sigma_mps"] if velocity is not None else params["unknown_velocity_sigma_mps"]
    x = np.concatenate([z, velocity if velocity is not None else np.zeros(3)])
    P = np.zeros((6, 6))
    P[:3, :3] = R
    P[3:, 3:] = np.eye(3) * sigma ** 2
    return Track(hex=m.hex, timestamp_s=m.position_us / 1e6, x=x, P=P)


def reported_velocity(m: Measurement) -> np.ndarray | None:
    """The velocity the plot itself reports, in ECEF metres per second, or None when it reports no ground speed or track angle."""
    if m.ground_speed_kt is None or m.track_deg is None:
        return None
    speed = m.ground_speed_kt / KNOTS
    east, north = speed * np.sin(np.radians(m.track_deg)), speed * np.cos(np.radians(m.track_deg))
    up = (m.vertical_rate_fpm or 0.0) * FEET / 60
    return np.array(pymap3d.enu2uvw(east, north, up, m.lat, m.lon))


def predict(track: Track, dt: float, params: dict, lat: float | None = None, lon: float | None = None) -> Track:
    """The track dt seconds later at constant velocity (earlier when dt is negative): the position moves, the uncertainty grows
    either way. Returns a new Track and leaves the given one as it is, so a plot that is then refused changes nothing. The process noise is set in east, north and up at
    (lat, lon), the track's own position when not given."""
    if lat is None or lon is None:
        lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
    F = np.eye(6)
    F[:3, 3:] = np.eye(3) * dt
    return Track(hex=track.hex, timestamp_s=track.timestamp_s + dt, x=F @ track.x, P=F @ track.P @ F.T + process_noise(abs(dt), params, lat, lon),
                 id=track.id, born_s=track.born_s, points=track.points, confirmed=track.confirmed)


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


def measurement_noise(sigma: float, m: Measurement, params: dict, velocity: np.ndarray) -> np.ndarray:
    """R: the plot's sigma east and north and the altitude sigma up, as a 3 by 3 matrix in ECEF. Along the direction of flight the plot may
    also be off by speed times its time error, because a plot whose time is off by t seconds shows where the aircraft was t
    seconds earlier or later; the two errors are independent, so their squares add."""
    east, north, _ = pymap3d.uvw2enu(*velocity, m.lat, m.lon)
    speed = float(np.hypot(east, north))
    horizontal = np.eye(2) * sigma ** 2
    if speed > 1.0 and m.time_sigma_s:
        direction = np.array([east, north]) / speed
        horizontal += (speed * m.time_sigma_s) ** 2 * np.outer(direction, direction)
    R = np.zeros((3, 3))
    R[:2, :2] = horizontal
    R[2, 2] = params["altitude_sigma_m"] ** 2   # the altitude comes from the barometric altimeter, not from the position fix
    return enu_to_ecef(R, m.lat, m.lon)


def enu_to_ecef(matrix_enu: np.ndarray, lat: float, lon: float) -> np.ndarray:
    """Rotate a 3 by 3 matrix given in east, north, up at (lat, lon) into ECEF axes."""
    # columns are the east, north and up unit vectors written in ECEF, so rotation @ v_enu is v_ecef
    rotation = np.array(pymap3d.enu2uvw(np.eye(3)[0], np.eye(3)[1], np.eye(3)[2], lat, lon))
    return rotation @ matrix_enu @ rotation.T


def distance(track: Track, z: np.ndarray, R: np.ndarray) -> dict[str, float]:
    """How far a position measurement z of uncertainty R is from where the track expects the aircraft: distance_m and
    distance_sigmas (below 3 in 97 of 100 plots if the noise is right; 10 is far off what we believed), and the same difference
    split along the direction of flight (along_m, positive when the plot is ahead) and across it (across_m)."""
    innovation = z - H @ track.x                       # how far the plot is from where we expected it
    S = H @ track.P @ H.T + R                          # how far off that difference may be
    along, across = along_across(innovation, track.x[3:])
    # the same miss split into horizontal and vertical, each in metres and in its own sigmas
    lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
    rotation = np.array(pymap3d.enu2uvw(np.eye(3)[0], np.eye(3)[1], np.eye(3)[2], lat, lon))
    miss_enu, S_enu = rotation.T @ innovation, rotation.T @ S @ rotation
    horizontal = miss_enu[:2] @ np.linalg.inv(S_enu[:2, :2]) @ miss_enu[:2]
    return dict(distance_m=float(np.linalg.norm(innovation)), distance_sigmas=float(np.sqrt(innovation @ np.linalg.inv(S) @ innovation)),
                along_m=along, across_m=across, vertical_m=float(miss_enu[2]),
                horizontal_sigmas=float(np.sqrt(horizontal)), vertical_sigmas=float(abs(miss_enu[2]) / np.sqrt(S_enu[2, 2])))


def correct(track: Track, z: np.ndarray, R: np.ndarray) -> None:
    """Pull the state toward a position measurement z of uncertainty R."""
    innovation = z - H @ track.x
    S = H @ track.P @ H.T + R
    K = track.P @ H.T @ np.linalg.inv(S)               # how much of the difference to believe
    track.x = track.x + K @ innovation
    track.P = (np.eye(6) - K @ H) @ track.P


def along_across(vector: np.ndarray, velocity: np.ndarray) -> tuple[float, float]:
    """A horizontal vector split into its part along the velocity and its part across it (both in metres; across is unsigned).
    A track that is not moving has no direction, so both are nan."""
    speed = np.linalg.norm(velocity)
    if speed < 1.0:
        return float("nan"), float("nan")
    direction = velocity / speed
    along = float(vector @ direction)
    across = float(np.linalg.norm(vector - along * direction))
    return along, across


class Kalman:
    name = "kalman"
    params = dict(
        spectral_density_horizontal=10.0,  # process noise east and north: how much the velocity may wander, (m/s^2)^2 * s.
                                           # 1.0 fits the median 60 s miss of straight flight but cannot follow a turn: with the
                                           # 5 sigma gate every turn became a 30 s loss; 10 follows turns at a rougher track
        spectral_density_vertical=0.5,     # process noise up. 0.02 fits the median 20 m altitude miss in 60 s but not the start of
                                           # a 3,000 ft/min descent; with a 10 m altitude sigma those plots were refused
        altitude_sigma_m=10.0,        # altitude error, one sigma: barometric altitude in 25 ft steps, the same whatever the position accuracy
        gate_sigmas=5.0,              # a plot farther than this from a track's prediction, in sigmas, does not belong to that track
        confirm_after_plots=3,        # a candidate track is published once this many plots agree with it
        confirm_within_s=30.0,        # a candidate that has not been confirmed this long after its first plot is dropped
        die_after_s=300.0,            # a track without a plot for this long is over
        reported_velocity_sigma_mps=10.0,  # how far off the ground speed and track a plot reports may be, per axis
        unknown_velocity_sigma_mps=300.0,  # a new track whose first plot reports no speed knows nothing about its velocity
    )

    def __init__(self, **overrides):
        self.params = {**Kalman.params, **overrides}
        self.tracks: dict[str, list[Track]] = {}   # per hex, the tracks alive: confirmed ones and candidates
        self.births: dict[str, int] = {}

    def update(self, m: Measurement) -> StrategyResult:
        reason = skip_reason(m)
        if reason:
            return StrategyResult.skipped(reason)

        z = np.array(pymap3d.geodetic2ecef(m.lat, m.lon, m.altitude_ft * FEET))
        sigma = measurement_sigma_m(m)
        timestamp_s = m.position_us / 1e6

        # the hex's tracks that are still alive, and for each how far the plot is from where the track is at the plot's time:
        # predicted forward for a plot newer than the track's last plot, backward for an older one. The plot goes to the newer
        # track it fits best. A plot older than a track's last plot that fits where the track was is a late copy of a plot we
        # had: it belongs to that track but is too late to use.
        tracks = [t for t in self.tracks.get(m.hex, []) if timestamp_s - t.timestamp_s < (self.params["die_after_s"] if t.confirmed else self.params["confirm_within_s"])]
        self.tracks[m.hex] = tracks
        best = late = None
        fits = []
        for track in tracks:
            predicted = predict(track, timestamp_s - track.timestamp_s, self.params, m.lat, m.lon)
            R = measurement_noise(sigma, m, self.params, predicted.x[3:])
            distances = distance(predicted, z, R)
            if timestamp_s <= track.timestamp_s:
                if distances["distance_sigmas"] <= self.params["gate_sigmas"] and (late is None or track.timestamp_s > late.timestamp_s):
                    late = track
                continue
            if distances["distance_sigmas"] <= self.params["gate_sigmas"]:
                fits.append(track)
            if best is None or distances["distance_sigmas"] < best[2]["distance_sigmas"]:
                best = (track, predicted, distances, R)
        if (best is None or best[2]["distance_sigmas"] > self.params["gate_sigmas"]) and late is not None:
            return StrategyResult.rejected(late.id, "same position time as the last used plot" if timestamp_s == late.timestamp_s else "out of order")

        # two tracks of one hex that both fit the same plot are one aircraft: the one the plot fits best goes on, the others end
        merged = 0
        for track in fits:
            if track is not best[0]:
                tracks.remove(track)
                merged += 1

        # a plot that fits no track is the first plot of a candidate track; a plot that fits one is pulled into it
        if best is None or best[2]["distance_sigmas"] > self.params["gate_sigmas"]:
            velocity = reported_velocity(m)
            R = measurement_noise(sigma, m, self.params, velocity if velocity is not None else np.zeros(3))
            track = start(m, z, R, self.params)
            track.id, track.born_s = f"{m.hex}:{sum(1 for _ in self.born(m.hex))}", timestamp_s
            tracks.append(track)
            numbers = dict(measurement_sigma_m=sigma, **(best[2] if best else {}))
            return self.record(track, m, numbers)
        track, predicted, distances, R = best
        correct(predicted, z, R)
        tracks[tracks.index(track)] = predicted
        return self.record(predicted, m, dict(measurement_sigma_m=sigma, **distances, **(dict(merged=float(merged)) if merged else {})))

    def born(self, hex: str):
        """Every track ever born for this hex, for numbering."""
        self.births = getattr(self, "births", {})
        self.births[hex] = self.births.get(hex, 0) + 1
        return range(self.births[hex])

    def record(self, track: Track, m: Measurement, numbers: dict) -> StrategyResult:
        """The plot went into the track: published at once when the track is confirmed; held when it is a candidate, and
        published with the candidate's earlier points when this plot confirms it."""
        point = track_point(track, m)
        if track.confirmed:
            return StrategyResult.used(TrackUpdate.append(track.id, point), **numbers)
        track.points.append(point)
        if len(track.points) < self.params["confirm_after_plots"]:
            return StrategyResult.rejected(track.id, f"candidate track, plot {len(track.points)} of {self.params['confirm_after_plots']}", **numbers)
        track.confirmed = True
        update = TrackUpdate(track.id, track.points[0].position_us, point.position_us, list(track.points))
        track.points = []
        return StrategyResult.used(update, confirmed=1.0, **numbers)

    @staticmethod
    def predict(state: dict[str, float], seconds: float, params: dict) -> dict:
        """Where the filter expects the aircraft `seconds` after one of its fused plots, by the same constant velocity
        step and process noise it runs on, from the state it recorded there."""
        track = predict(from_state(state), seconds, {**Kalman.params, **params})
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


def track_point(track: Track, m: Measurement) -> TrackPoint:
    """The corrected state as one point of the track, with the filter's sigmas and its state for predict()."""
    lat, lon, altitude_m = pymap3d.ecef2geodetic(*track.x[:3])
    east, north, _ = pymap3d.uvw2enu(*track.x[3:], lat, lon)
    point = TrackPoint(position_us=m.position_us, source_received_us=m.source_received_us, received_us=m.received_us,
                       lat=float(lat), lon=float(lon), altitude_ft=int(round(altitude_m / FEET)),
                       ground_speed_kt=float(np.hypot(east, north) * KNOTS), track_deg=float(np.degrees(np.arctan2(east, north)) % 360),
                       hex=m.hex, callsign=m.callsign, tail=m.tail, squawk=m.squawk, track_identifier=m.track_identifier,
                       source_identifier=m.source_identifier, numbers={**sigmas(track), **state_numbers(track)})
    return point
