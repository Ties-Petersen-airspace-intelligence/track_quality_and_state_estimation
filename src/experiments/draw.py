"""One picture per case: map and altitude for the whole hour and zoomed on the event window, the filter's distance-in-sigmas per used
plot, speed, and the filter's own sigma next to the measurement sigma. Raw plots by source, the filter's track white, production
regular pink. Rejected raw plots get a red ring, skipped ones a grey ring."""
from __future__ import annotations

import datetime as dt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .run import local_xy, jumps

BG, PANEL, LINE, FG, MUTED = "#0a0b0d", "#15171a", "#363a41", "#ffffff", "#8e949c"
SOURCE_COLOR = {"adsbx": "#3987e5", "uavionix": "#d95926", "planefinder": "#199e70", "tfms_ti": "#c98500", "stdds": "#9085e9", "tfms_or": "#d55181", "ual": "#e66767", "asa": "#008300"}
KALMAN, PROD = "#ffffff", "#e87ba4"
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": PANEL, "axes.edgecolor": LINE, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "text.color": FG, "grid.color": LINE, "axes.grid": True, "grid.linewidth": 0.5, "font.size": 8, "legend.facecolor": PANEL, "legend.edgecolor": LINE,
                     "axes.titlecolor": FG, "axes.titlesize": 9, "axes.titlelocation": "left"})


def clock(us) -> np.ndarray:
    return np.array([dt.datetime.utcfromtimestamp(u / 1e6) for u in np.asarray(us, float)])


def event_window(data: dict, result: dict) -> tuple[int, int]:
    """The event time from case.json, else the time of production regular's largest jump; plus or minus 150 seconds."""
    event = (data["info"].get("event") or {}).get("t")
    if event:
        centre = int(pd.Timestamp(event).tz_localize("UTC").timestamp() * 1e6)
    else:
        raw = result["raw"]
        lat0, lon0 = float(np.median(raw["lat"])), float(np.median(raw["lon"]))
        j = jumps(data["regular"], lat0, lon0)
        centre = int(j.loc[j["jump_m"].idxmax(), "position_us"]) if len(j) else int(raw["position_us"].median())
    return centre - 150_000_000, centre + 150_000_000


def draw(data: dict, result: dict, path, title_extra: str = "") -> None:
    raw, track, info = result["raw"], result["track"], data["info"]
    lat0, lon0 = float(np.median(raw["lat"])), float(np.median(raw["lon"]))
    since, until = event_window(data, result)
    fig, axes = plt.subplots(3, 2, figsize=(14, 12), gridspec_kw=dict(width_ratios=[1, 1]))
    fig.suptitle(f"{info['name']}   {info['suspect'].get('callsign', '')} {info['suspect']['hex']}   {title_extra}\n{info.get('reason', '')[:150]}", fontsize=9, x=0.01, ha="left")

    for column, window in enumerate((None, (since, until))):
        r = raw if window is None else raw[(raw["position_us"] >= window[0]) & (raw["position_us"] <= window[1])]
        t = track if window is None else track[(track["position_us"] >= window[0]) & (track["position_us"] <= window[1])]
        p = data["regular"] if window is None else data["regular"][(data["regular"]["position_us"] >= window[0]) & (data["regular"]["position_us"] <= window[1])]
        map_panel(axes[0, column], r, t, p, lat0, lon0, "whole hour" if window is None else "event window, 5 minutes")
        altitude_panel(axes[1, column], r, t, p, "altitude, whole hour" if window is None else "altitude, event window")
        if window is not None and len(r):
            for ax in axes[:, 1]:
                pass
    sigmas_panel(axes[2, 0], raw, since, until)
    speed_panel(axes[2, 1], raw, track, data["regular"], since, until)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=90)
    plt.close(fig)


def scatter_raw(ax, r: pd.DataFrame, x, y, size=6):
    for source, color in SOURCE_COLOR.items():
        s = r[r["source"] == source]
        if not len(s):
            continue
        own = s[s["kind"] != "mlat"]; mlat = s[s["kind"] == "mlat"]
        ax.scatter(x[own.index], y[own.index], s=size, c=color, label=f"{source} ({len(s)})", zorder=3, linewidths=0)
        if len(mlat):
            ax.scatter(x[mlat.index], y[mlat.index], s=size * 2, marker="x", c=color, label=f"{source} mlat ({len(mlat)})", zorder=3, linewidths=0.6)
    for state, color, label in (("rejected", "#d03b3b", "rejected"), ("skipped", "#8e949c", "skipped"), ("removed", "#fab219", "removed")):
        s = r[r["state"] == state]
        if len(s):
            ax.scatter(x[s.index], y[s.index], s=size * 5, facecolors="none", edgecolors=color, linewidths=0.6, label=f"{label} ({len(s)})", zorder=4)


def map_panel(ax, r, t, p, lat0, lon0, title):
    ax.set_title(title); ax.set_aspect("equal")
    if len(r):
        east, north = local_xy(r["lat"], r["lon"], r["altitude_ft"], lat0, lon0)
        east, north = pd.Series(east / 1000, index=r.index), pd.Series(north / 1000, index=r.index)
        scatter_raw(ax, r, east, north)
    if len(p):
        e, n = local_xy(p["lat"], p["lon"], p["altitude_ft"], lat0, lon0)
        ax.plot(e / 1000, n / 1000, color=PROD, lw=0.8, alpha=0.9, label=f"prod regular ({len(p)})", zorder=5)
    if len(t):
        e, n = local_xy(t["lat"], t["lon"], t["altitude_ft"], lat0, lon0)
        ax.plot(e / 1000, n / 1000, color=KALMAN, lw=0.9, label=f"kalman ({len(t)})", zorder=6)
    ax.set_xlabel("east km"); ax.set_ylabel("north km"); ax.legend(fontsize=6, loc="best", markerscale=1.5)


def altitude_panel(ax, r, t, p, title):
    ax.set_title(title)
    if len(r):
        scatter_raw(ax, r, pd.Series(clock(r["position_us"]), index=r.index), r["altitude_ft"])
    if len(p):
        ax.plot(clock(p["position_us"]), p["altitude_ft"], color=PROD, lw=0.8, label="prod regular", zorder=5)
    if len(t):
        ax.plot(clock(t["position_us"]), t["altitude_ft"], color=KALMAN, lw=0.9, label="kalman", zorder=6)
    ax.set_ylabel("ft"); ax.legend(fontsize=6, loc="best"); ax.tick_params(axis="x", labelrotation=0)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))


def sigmas_panel(ax, raw, since, until):
    ax.set_title("distance of each plot from the prediction, in sigmas (log); red rings: rejected as too far; lime line: restart")
    used = raw[(raw["state"] == "used") & raw.get("distance_sigmas", pd.Series(dtype=float)).notna()] if "distance_sigmas" in raw else raw.iloc[0:0]
    if len(used):
        x = pd.Series(clock(used["position_us"]), index=used.index)
        scatter_raw(ax, used, x, used["distance_sigmas"].clip(lower=0.01))
        ax.set_yscale("log"); ax.axhline(3, color=MUTED, lw=0.5, ls="--"); ax.axhline(5, color="#d03b3b", lw=0.5, ls="--")
    far = raw[(raw["state"] == "rejected") & raw.get("distance_sigmas", pd.Series(dtype=float)).notna()] if "distance_sigmas" in raw else raw.iloc[0:0]
    if len(far):
        ax.scatter(clock(far["position_us"]), far["distance_sigmas"].clip(lower=0.01), s=20, facecolors="none", edgecolors="#d03b3b", linewidths=0.6, label=f"rejected, far ({len(far)})", zorder=4)
    if "restarted" in raw:
        for t in raw.loc[raw["restarted"] == 1.0, "position_us"]:
            ax.axvline(clock([t])[0], color="#ccff00", lw=0.8, alpha=0.8)
    ax.axvspan(clock([since])[0], clock([until])[0], color="#ccff00", alpha=0.06, lw=0)
    ax.set_ylabel("sigmas"); ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    if len(used) or len(far):
        ax.legend(fontsize=6, loc="upper left")


def speed_panel(ax, raw, track, p, since, until):
    ax.set_title("ground speed: raw plots (dots), kalman (white), prod regular (pink); shaded: event window")
    if len(raw):
        scatter_raw(ax, raw, pd.Series(clock(raw["position_us"]), index=raw.index), raw["ground_speed_kt"], size=4)
    if len(p):
        ax.plot(clock(p["position_us"]), p["ground_speed_kt"], color=PROD, lw=0.7, zorder=5)
    if len(track):
        ax.plot(clock(track["position_us"]), track["ground_speed_kt"], color=KALMAN, lw=0.8, zorder=6)
    ax.axvspan(clock([since])[0], clock([until])[0], color="#ccff00", alpha=0.06, lw=0)
    ax.set_ylabel("kt"); ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
