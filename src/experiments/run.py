"""Run the normalizer and the Kalman strategy on one case's suspect aircraft and return plain tables about it: what happened to each
raw plot, the filter's track, and a few numbers. Nothing is written to the case folder; the harness's own runs stay untouched."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pymap3d

from harness.normalization.basic import Basic
from harness.strategies.kalman import Kalman

FEET = 0.3048


def run(data: dict, strategy_overrides: dict | None = None, normalizer_overrides: dict | None = None) -> dict:
    """raw: one row per raw plot with state, reason, the strategy's numbers and the plot's own fields; track: one row per fused point."""
    normalizer, strategy = Basic(**(normalizer_overrides or {})), Kalman(**(strategy_overrides or {}))
    raw_rows, track_rows = [], []
    for plot in data["plots"]:
        normalized = normalizer.normalize(plot)
        m = normalized.measurement
        row = dict(source=plot.source, row=plot.row, received_us=plot.received_us, position_us=plot.position_us,
                   lat=plot.proto.common.latitude, lon=plot.proto.common.longitude,
                   altitude_ft=plot.proto.common.altitude_ft if plot.proto.common.HasField("altitude_ft") else np.nan,
                   ground_speed_kt=plot.proto.common.ground_speed_kt if plot.proto.common.HasField("ground_speed_kt") else np.nan,
                   state=normalized.state, reason=normalized.reason, kind="", accuracy_95_m=np.nan)
        if m is None:
            raw_rows.append(row); continue
        row.update(kind=m.kind, accuracy_95_m=m.accuracy_95_m if m.accuracy_95_m is not None else np.nan)
        result = strategy.update(m)
        row.update(state=result.state, reason=result.reason, **result.numbers)
        raw_rows.append(row)
        if result.update:
            for point in result.update.points:
                track_rows.append(dict(position_us=point.position_us, received_us=point.received_us, lat=point.lat, lon=point.lon,
                                       altitude_ft=point.altitude_ft, ground_speed_kt=point.ground_speed_kt, track_deg=point.track_deg,
                                       source=plot.source, **{k: v for k, v in point.numbers.items() if not k.startswith("state_")}))
    raw = pd.DataFrame(raw_rows)
    track = pd.DataFrame(track_rows)
    return dict(raw=raw, track=track, params=dict(strategy.params), normalizer_params=dict(normalizer.params))


def local_xy(lat, lon, alt_ft, lat0: float, lon0: float) -> tuple[np.ndarray, np.ndarray]:
    """East and north in metres from (lat0, lon0), altitude included so distances are true 3D-ish (up is dropped)."""
    east, north, _ = pymap3d.geodetic2enu(np.asarray(lat, float), np.asarray(lon, float), np.nan_to_num(np.asarray(alt_ft, float)) * FEET, lat0, lon0, 0.0)
    return east, north


def jumps(track: pd.DataFrame, lat0: float, lon0: float) -> pd.DataFrame:
    """Between consecutive points in position time: the horizontal jump in metres, the seconds between them, the implied speed in
    knots, and the altitude step in feet."""
    if len(track) < 2:
        return pd.DataFrame(columns=["position_us", "jump_m", "dt_s", "implied_kt", "altitude_step_ft"])
    t = track.sort_values("position_us")
    east, north = local_xy(t["lat"], t["lon"], t["altitude_ft"], lat0, lon0)
    jump = np.hypot(np.diff(east), np.diff(north))
    dt = np.diff(t["position_us"].to_numpy(float)) / 1e6
    alt = np.abs(np.diff(np.nan_to_num(t["altitude_ft"].to_numpy(float))))
    return pd.DataFrame(dict(position_us=t["position_us"].to_numpy()[1:], jump_m=jump, dt_s=dt, implied_kt=np.where(dt > 0, jump / np.maximum(dt, 1e-3) * 1.943844, np.nan), altitude_step_ft=alt))


def numbers(result: dict, data: dict) -> dict:
    """The few numbers per case that the summary table shows, for the filter and for production's two tracks."""
    info = data["info"]
    lat0, lon0 = float(np.median(result["raw"]["lat"])), float(np.median(result["raw"]["lon"]))
    raw, track = result["raw"], result["track"]
    out = dict(case=info["name"], suspect=info["suspect"].get("callsign", ""), kind=(info.get("event") or {}).get("kind", "") or "named case",
               raw_plots=len(raw), used=int((raw["state"] == "used").sum()), skipped=int((raw["state"] == "skipped").sum()),
               rejected=int((raw["state"] == "rejected").sum()), removed=int((raw["state"] == "removed").sum()))
    out["reasons"] = "; ".join(f"{k} {v}" for k, v in raw.loc[raw["state"].isin(["rejected", "skipped"]), "reason"].value_counts().items())
    used = raw[raw["state"] == "used"]
    if "distance_sigmas" in used:
        s = used["distance_sigmas"].dropna()
        out.update(median_sigmas=round(float(s.median()), 2) if len(s) else np.nan, over_5_sigma_pct=round(float((s > 5).mean() * 100), 1) if len(s) else np.nan)
    for name, frame in (("kalman", track), ("append", data["append"]), ("regular", data["regular"])):
        j = jumps(frame, lat0, lon0)
        out[f"{name}_points"] = len(frame)
        out[f"{name}_max_jump_m"] = round(float(j["jump_m"].max()), 0) if len(j) else np.nan
        out[f"{name}_max_implied_kt"] = round(float(j["implied_kt"].max()), 0) if len(j) else np.nan
        out[f"{name}_max_alt_step_ft"] = round(float(j["altitude_step_ft"].max()), 0) if len(j) else np.nan
        out[f"{name}_max_speed_kt"] = round(float(frame["ground_speed_kt"].max()), 0) if len(frame) and frame["ground_speed_kt"].notna().any() else np.nan
    return out
