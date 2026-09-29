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


@dataclass(eq=False)
class Model:
    """One motion hypothesis inside an object: a constant velocity filter with its own process noise."""
    x: np.ndarray       # state: x, y, z, vx, vy, vz in ECEF, metres and metres per second
    P: np.ndarray       # uncertainty of the state, 6 by 6


@dataclass(eq=False)   # objects are compared by identity, never by their arrays
class Track:
    """A tracked object. Two models run side by side on the same plots, straight flight (small process noise) and manoeuvre
    (large process noise), with weights that say how much each describes what the aircraft is doing now. The object's own
    position, velocity and uncertainty are the weighted mix of the two (x and P below)."""
    hex: str
    timestamp_s: float  # seconds, position time of the last used plot
    models: list[Model]                    # straight, manoeuvre
    mu: np.ndarray                         # their weights, adding up to one
    id: str = ""        # hex:n, n counting the objects born for this hex
    born_s: float = 0.0                                   # position time of the first plot
    points: list[TrackPoint] = field(default_factory=list)  # a candidate's points, published together when it is confirmed
    confirmed: bool = False
    rejected_since_s: float | None = None   # position time of the first plot refused since the last used one; None when none was

    @property
    def x(self) -> np.ndarray:
        return sum(w * m.x for w, m in zip(self.mu, self.models))

    @property
    def P(self) -> np.ndarray:
        x = self.x
        return sum(w * (m.P + np.outer(m.x - x, m.x - x)) for w, m in zip(self.mu, self.models))


def start(m: Measurement, z: np.ndarray, R: np.ndarray, params: dict) -> Track:
    """A new object at the plot's position, moving as the plot reports (ground speed, track angle, vertical rate); a plot that
    reports no speed gives an object that knows nothing about its velocity. Both models start the same; the straight one
    carries most of the weight."""
    velocity = reported_velocity(m)
    sigma = params["reported_velocity_sigma_mps"] if velocity is not None else params["unknown_velocity_sigma_mps"]
    x = np.concatenate([z, velocity if velocity is not None else np.zeros(3)])
    P = np.zeros((6, 6))
    P[:3, :3] = R
    P[3:, 3:] = np.eye(3) * sigma ** 2
    return Track(hex=m.hex, timestamp_s=m.position_us / 1e6, models=[Model(x.copy(), P.copy()), Model(x.copy(), P.copy())],
                 mu=np.array([1 - params["start_manoeuvre_weight"], params["start_manoeuvre_weight"]]))


def reported_velocity(m: Measurement) -> np.ndarray | None:
    """The velocity the plot itself reports, in ECEF metres per second, or None when it reports no ground speed or track angle."""
    if m.ground_speed_kt is None or m.track_deg is None:
        return None
    speed = m.ground_speed_kt / KNOTS
    east, north = speed * np.sin(np.radians(m.track_deg)), speed * np.cos(np.radians(m.track_deg))
    up = (m.vertical_rate_fpm or 0.0) * FEET / 60
    return np.array(pymap3d.enu2uvw(east, north, up, m.lat, m.lon))


def predict(track: Track, dt: float, params: dict, lat: float | None = None, lon: float | None = None) -> Track:
    """The object dt seconds later (earlier when dt is negative). First the interacting step: each model starts from a blend
    of both models' states, weighted by how likely a switch between straight flight and manoeuvring is over dt. Then each model
    moves at constant velocity and its uncertainty grows by its own process noise. Returns a new Track and leaves the given
    one as it is, so a plot that is then refused changes nothing."""
    if lat is None or lon is None:
        lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
    switch = 1 - np.exp(-abs(dt) / params["switch_time_s"])
    transition = np.array([[1 - switch, switch], [switch, 1 - switch]])   # row: from, column: to
    mu_predicted = transition.T @ track.mu
    F = np.eye(6)
    F[:3, 3:] = np.eye(3) * dt
    densities = ((params["spectral_density_straight"], params["spectral_density_vertical"]),
                 (params["spectral_density_manoeuvre"], params["spectral_density_vertical_manoeuvre"]))
    models = []
    for j, (q, q_up) in enumerate(densities):
        weights = transition[:, j] * track.mu / mu_predicted[j]                    # how much of each model goes into model j
        x0 = sum(w * m.x for w, m in zip(weights, track.models))
        P0 = sum(w * (m.P + np.outer(m.x - x0, m.x - x0)) for w, m in zip(weights, track.models))
        models.append(Model(F @ x0, F @ P0 @ F.T + process_noise(abs(dt), q, q_up, lat, lon)))
    return Track(hex=track.hex, timestamp_s=track.timestamp_s + dt, models=models, mu=mu_predicted,
                 id=track.id, born_s=track.born_s, points=track.points, confirmed=track.confirmed, rejected_since_s=track.rejected_since_s)


def process_noise(dt: float, horizontal: float, vertical: float, lat: float, lon: float) -> np.ndarray:
    """Q for a velocity that wanders like white noise, with one spectral density east and north and another up, rotated from
    east, north, up at (lat, lon) into ECEF."""
    q = np.diag([horizontal] * 2 + [vertical])
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
    """Pull each model toward the position measurement z of uncertainty R, and move the weights toward the model under whose
    prediction the plot was more likely."""
    likelihoods = []
    for model in track.models:
        innovation = z - H @ model.x
        S = H @ model.P @ H.T + R
        S_inverse = np.linalg.inv(S)
        K = model.P @ H.T @ S_inverse                  # how much of the difference to believe
        model.x = model.x + K @ innovation
        model.P = (np.eye(6) - K @ H) @ model.P
        likelihoods.append(np.exp(-0.5 * innovation @ S_inverse @ innovation) / np.sqrt(np.linalg.det(2 * np.pi * S)))
    mu = track.mu * np.array(likelihoods)
    track.mu = mu / mu.sum() if mu.sum() > 0 else track.mu


def horizontal_distance_m(z: np.ndarray, track: Track) -> float:
    """How far a position z is from the track's position, over the ground."""
    lat, lon, _ = pymap3d.ecef2geodetic(*track.x[:3])
    east, north, _ = pymap3d.ecef2enu(*z, lat, lon, 0.0)
    return float(np.hypot(east, north))


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
        spectral_density_straight=1.0,     # process noise east and north of the straight-flight model, (m/s^2)^2 * s: fits the
                                           # median 60 s miss of straight flight
        spectral_density_manoeuvre=100.0,  # the same for the manoeuvre model: follows a standard-rate turn (Dubai: 2 losses in 80 objects)
        spectral_density_vertical=0.5,     # process noise up of the straight model. 0.02 fits the median 20 m altitude miss in 60 s but
                                           # not the start of a 3,000 ft/min descent; with a 10 m altitude sigma those plots were refused
        spectral_density_vertical_manoeuvre=20.0, # the same for the manoeuvre model: a manoeuvre changes the vertical rate too (a light
                                           # aircraft over Dubai dropped 675 ft in an 8 s gap; 0.5 refused every plot after it)
        switch_time_s=120.0,               # how long straight flight or a manoeuvre typically lasts: the chance per second of a switch
                                           # between the two models is 1 over this
        start_manoeuvre_weight=0.1,        # a new object is believed to fly straight with this much doubt
        altitude_sigma_m=10.0,        # altitude error, one sigma: barometric altitude in 25 ft steps, the same whatever the position accuracy
        gate_sigmas=5.0,              # a plot farther than this from an object's prediction, in sigmas, does not belong to that object
        restart_after_s=30.0,         # after refusing every reachable plot for this long an object has lost its aircraft and starts over
        birth_speed_margin=2.0,       # a new object is born only where no live object could have flown: farther than this x speed x time
        confirm_after_s=300.0,        # a further object of a hex is published once plots have agreed with it for this long (Ties, 28 Sep: 5 min)
        die_after_s=300.0,            # an object, candidate or confirmed, without a plot for this long is over
        reported_velocity_sigma_mps=10.0,  # how far off the ground speed and track a plot reports may be, per axis
        unknown_velocity_sigma_mps=300.0,  # a new track whose first plot reports no speed knows nothing about its velocity
    )

    def __init__(self, **overrides):
        self.params = {**Kalman.params, **overrides}
        self.tracks: dict[str, list[Track]] = {}   # per hex, the objects alive: confirmed ones and candidates
        self.births: dict[str, int] = {}          # per hex, how many objects were ever born, for their ids

    def update(self, m: Measurement) -> StrategyResult:
        reason = skip_reason(m)
        if reason:
            return StrategyResult.skipped(reason)

        z = np.array(pymap3d.geodetic2ecef(m.lat, m.lon, m.altitude_ft * FEET))
        sigma = measurement_sigma_m(m)
        timestamp_s = m.position_us / 1e6

        # the hex's objects still alive (a plot in the last die_after_s), and for each how far the plot is from where the object
        # is at the plot's time: predicted forward for a plot newer than the object's last plot, backward for an older one
        objects = [t for t in self.tracks.get(m.hex, []) if timestamp_s - t.timestamp_s < self.params["die_after_s"]]
        self.tracks[m.hex] = objects
        fits, late = [], None
        for track in objects:
            predicted = predict(track, timestamp_s - track.timestamp_s, self.params, m.lat, m.lon)
            R = measurement_noise(sigma, m, self.params, predicted.x[3:])
            distances = distance(predicted, z, R)
            within = distances["distance_sigmas"] <= self.params["gate_sigmas"]
            if timestamp_s <= track.timestamp_s:
                if within and (late is None or track.timestamp_s > late.timestamp_s):
                    late = track
            elif within:
                fits.append((track, predicted, distances, R))

        # the plot fits an object: into the one it fits best; objects that fit the same plot are one aircraft, the oldest goes on
        if fits:
            fits.sort(key=lambda f: f[2]["distance_sigmas"])
            track, predicted, distances, R = fits[0]
            for other, *_ in fits[1:]:
                if other.born_s < track.born_s:
                    track, predicted, distances, R = other, *[f for f in fits if f[0] is other][0][1:]
            for other, *_ in fits:
                if other is not track:
                    objects.remove(other)
            correct(predicted, z, R)
            predicted.rejected_since_s = None
            objects[objects.index(track)] = predicted
            numbers = dict(measurement_sigma_m=sigma, **distances, **(dict(merged=float(len(fits) - 1)) if len(fits) > 1 else {}))
            return self.record(predicted, m, numbers)

        # the plot fits where an object was: a late copy of a plot the object already has
        if late is not None:
            return StrategyResult.rejected(late.id, "same position time as the last used plot" if timestamp_s == late.timestamp_s else "out of order")

        # the plot fits no object. Could one of them have flown here since its last plot? Then the plot is an outlier or the
        # object is lagging: refused, and after 30 s of such refusals the nearest object admits it is lost and starts over here
        if objects:
            speed = max(max(float(np.linalg.norm(t.x[3:])) for t in objects), (m.ground_speed_kt or 0.0) / KNOTS)
            nearest = min(objects, key=lambda t: horizontal_distance_m(z, t))
            elapsed_s = max(abs(timestamp_s - nearest.timestamp_s), 1.0)
            if horizontal_distance_m(z, nearest) <= self.params["birth_speed_margin"] * speed * elapsed_s:
                if timestamp_s <= nearest.timestamp_s:
                    return StrategyResult.rejected(nearest.id, "out of order")
                nearest.rejected_since_s = nearest.rejected_since_s if nearest.rejected_since_s is not None else timestamp_s
                if timestamp_s - nearest.rejected_since_s < self.params["restart_after_s"] or not nearest.confirmed:
                    predicted = predict(nearest, timestamp_s - nearest.timestamp_s, self.params, m.lat, m.lon)
                    distances = distance(predicted, z, measurement_noise(sigma, m, self.params, predicted.x[3:]))
                    return StrategyResult.rejected(nearest.id, "far from the prediction", measurement_sigma_m=sigma, **distances)
                velocity = reported_velocity(m)
                restarted = start(m, z, measurement_noise(sigma, m, self.params, velocity if velocity is not None else np.zeros(3)), self.params)
                restarted.id, restarted.born_s, restarted.confirmed = nearest.id, nearest.born_s, True
                objects[objects.index(nearest)] = restarted
                return self.record(restarted, m, dict(measurement_sigma_m=sigma, restarted=1.0))

        # no live object could be here: a new object. The first object of a hex is published at once; a further one, another
        # aircraft under this hex until proven otherwise, starts as a candidate that must earn publication
        velocity = reported_velocity(m)
        track = start(m, z, measurement_noise(sigma, m, self.params, velocity if velocity is not None else np.zeros(3)), self.params)
        self.births[m.hex] = self.births.get(m.hex, 0) + 1
        track.id, track.born_s, track.confirmed = f"{m.hex}:{self.births[m.hex]}", timestamp_s, not objects
        objects.append(track)
        return self.record(track, m, dict(measurement_sigma_m=sigma))

    def record(self, track: Track, m: Measurement, numbers: dict) -> StrategyResult:
        """The plot went into the object: published at once when the object is confirmed; held while it is a candidate, and
        published with the candidate's earlier points when plots have agreed with it for confirm_after_s."""
        point = track_point(track, m)
        if track.confirmed:
            return StrategyResult.used(TrackUpdate.append(track.id, point), **numbers)
        track.points.append(point)
        if track.timestamp_s - track.born_s < self.params["confirm_after_s"]:
            return StrategyResult.rejected(track.id, f"candidate object, {track.timestamp_s - track.born_s:.0f} s old", **numbers)
        track.confirmed = True
        update = TrackUpdate(track.id, track.points[0].position_us, point.position_us, list(track.points))
        track.points = []
        return StrategyResult.used(update, confirmed=1.0, **numbers)

    @staticmethod
    def predict(state: dict[str, float], seconds: float, params: dict) -> dict:
        """Where the object expects the aircraft `seconds` after one of its track points, by the same two-model step it runs
        on, from the state it recorded there: the weighted mix, and each model on its own with its weight."""
        now = from_state(state)
        track = predict(now, seconds, {**Kalman.params, **params})
        out = ellipse(track.x, track.P)
        # each model's weight is the one at the track point itself, the same number the point records as manoeuvre_weight;
        # the prediction's own mixing weights are not shown
        out["models"] = [dict(name=name, weight=float(w), **ellipse(model.x, model.P)) for name, w, model in zip(MODEL_NAMES, now.mu, track.models)]
        return out


def ellipse(x: np.ndarray, P: np.ndarray) -> dict:
    lat, lon, _ = pymap3d.ecef2geodetic(*x[:3])
    s = sigmas_of(x, P)
    return dict(latitude=float(lat), longitude=float(lon), sigma_east_m=s["sigma_east_m"], sigma_north_m=s["sigma_north_m"], cov_east_north_m2=s["cov_east_north_m2"])


# each model's state x in ECEF, then its P by its upper triangle, then the weights, as named numbers of a track point
STATE_NAMES = ["x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps"]
MODEL_NAMES = ["straight", "manoeuvre"]


def state_numbers(track: Track) -> dict[str, float]:
    out = {}
    for name, model in zip(MODEL_NAMES, track.models):
        out.update({f"{STATE_PREFIX}{name}_{n}": float(v) for n, v in zip(STATE_NAMES, model.x)})
        out.update({f"{STATE_PREFIX}{name}_p_{i}_{j}": float(model.P[i, j]) for i in range(6) for j in range(i, 6)})
    out.update({f"{STATE_PREFIX}weight_{name}": float(w) for name, w in zip(MODEL_NAMES, track.mu)})
    return out


def from_state(state: dict[str, float]) -> Track:
    models = []
    for name in MODEL_NAMES:
        P = np.zeros((6, 6))
        for i in range(6):
            for j in range(i, 6):
                P[i, j] = P[j, i] = state[f"{STATE_PREFIX}{name}_p_{i}_{j}"]
        models.append(Model(np.array([state[f"{STATE_PREFIX}{name}_{n}"] for n in STATE_NAMES]), P))
    return Track(hex="", timestamp_s=0.0, models=models, mu=np.array([state[f"{STATE_PREFIX}weight_{name}"] for name in MODEL_NAMES]))


def sigmas(track: Track) -> dict[str, float]:
    """The object's own sigmas at this moment, from the mix of its models, plus the manoeuvre weight."""
    out = sigmas_of(track.x, track.P)
    out["manoeuvre_weight"] = float(track.mu[1])
    return out


def sigmas_of(x: np.ndarray, P: np.ndarray) -> dict[str, float]:
    """East, north, up sigmas in metres and horizontal speed sigma in metres per second, and the east-north covariance in
    square metres, which with the two sigmas gives the horizontal uncertainty ellipse. P is in ECEF, so its position and
    velocity blocks are rotated into east, north, up at the position."""
    lat, lon, _ = pymap3d.ecef2geodetic(*x[:3])
    rotation = np.array(pymap3d.enu2uvw(np.eye(3)[0], np.eye(3)[1], np.eye(3)[2], lat, lon))
    position = rotation.T @ P[:3, :3] @ rotation
    velocity = rotation.T @ P[3:, 3:] @ rotation
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
