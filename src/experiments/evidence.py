"""Cross-case figures that show a cause, not one case: drawn from the per-case raw and track tables an iteration saved."""
from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .draw import SOURCE_COLOR, MUTED

SIGMA_BINS = np.logspace(-2, 4, 61)


def load(out: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.concat([pd.read_parquet(p) for p in sorted(out.glob("*_raw.parquet"))], ignore_index=True)
    track = pd.concat([pd.read_parquet(p) for p in sorted(out.glob("*_track.parquet"))], ignore_index=True)
    return raw, track


def draw_all(out: pathlib.Path) -> None:
    raw, track = load(out)
    used = raw[(raw["state"] == "used") & raw["distance_sigmas"].notna()]
    sigmas_by_speed(used, out / "evidence_sigmas_by_speed.png")
    sigma_histogram(used, out / "evidence_sigma_histogram.png")
    used.groupby(["case", "source", "kind"])["distance_sigmas"].median().unstack(["source", "kind"]).round(2).to_csv(out / "evidence_median_sigmas.csv")
    if "along_m" in used:
        along_across_by_speed(used, out / "evidence_along_across.png")
    start_speed(raw, track, out / "evidence_start_speed.png")


def sigmas_by_speed(used: pd.DataFrame, path) -> None:
    """Per case and source: the median distance in sigmas against the median reported ground speed. If the measurement noise were
    right, every point would sit near 1 whatever the speed."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_title("median distance from the prediction, in sigmas, per case and source, against speed")
    for (case, source, kind), g in used.groupby(["case", "source", "kind"]):
        if len(g) < 20:
            continue
        speed = g["ground_speed_kt"].median()
        ax.scatter(speed, g["distance_sigmas"].median(), s=18, c=SOURCE_COLOR.get(source, "#888"), marker="x" if kind == "mlat" else "o", linewidths=0.8)
    for source, color in SOURCE_COLOR.items():
        if source in set(used["source"]):
            ax.scatter([], [], c=color, label=source)
    ax.scatter([], [], c=MUTED, marker="x", label="mlat")
    ax.axhline(1, color=MUTED, lw=0.6, ls="--"); ax.set_yscale("log"); ax.set_xlabel("median reported ground speed, kt"); ax.set_ylabel("median sigmas (log)")
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def sigma_histogram(used: pd.DataFrame, path) -> None:
    """All used plots of all cases: how far they were from the prediction in sigmas. The tail past 10 sigma is plots that
    should not have been believed as they were."""
    fig, ax = plt.subplots(figsize=(9, 4))
    s = used["distance_sigmas"].clip(lower=0.01, upper=9999)
    counts, _ = np.histogram(s, bins=SIGMA_BINS)
    ax.bar(SIGMA_BINS[:-1], counts, width=np.diff(SIGMA_BINS), align="edge", color="#3987e5", linewidth=0)
    ax.set_xscale("log"); ax.set_yscale("log")
    for x, label in ((3, "3"), (5, "5"), (10, "10"), (100, "100")):
        ax.axvline(x, color="#d03b3b" if x >= 5 else MUTED, lw=0.6, ls="--")
    tail = int((s > 10).sum()); over5 = int((s > 5).sum())
    ax.set_title(f"distance from the prediction of every used plot, {len(s)} plots, 34 cases: {over5} over 5 sigma ({over5 / len(s) * 100:.1f}%), {tail} over 10 sigma ({tail / len(s) * 100:.1f}%)")
    ax.set_xlabel("sigmas (log)"); ax.set_ylabel("plots (log)")
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def along_across_by_speed(used: pd.DataFrame, path) -> None:
    """Per case and source: the spread (68th percentile of the absolute value, one sigma for a normal spread) of the miss along
    the direction of flight and across it, against speed. A time error shows as an along-track spread that grows with speed
    while the across-track spread stays flat. The dotted lines are speed times a time error of 0.1, 0.3 and 0.6 s."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, column, title in ((axes[0], "along_m", "along the direction of flight"), (axes[1], "across_m", "across it")):
        ax.set_title(f"spread of the miss {title}, per case and source, against speed")
        for (case, source, kind), g in used.groupby(["case", "source", "kind"]):
            g = g.dropna(subset=[column])
            if len(g) < 20 or kind == "mlat":
                continue
            ax.scatter(g["ground_speed_kt"].median(), np.percentile(np.abs(g[column]), 68), s=18, c=SOURCE_COLOR.get(source, "#888"), linewidths=0)
        speeds = np.linspace(50, 550, 10)
        for seconds in (0.1, 0.3, 0.6):
            ax.plot(speeds, speeds / 1.943844 * seconds, color=MUTED, lw=0.5, ls=":")
            ax.text(550, 550 / 1.943844 * seconds, f"{seconds} s", color=MUTED, fontsize=7, va="center")
        ax.set_yscale("log"); ax.set_ylim(1, 1000); ax.set_xlabel("median reported ground speed, kt"); ax.set_ylabel("68th percentile of |miss|, m (log)")
    for source, color in SOURCE_COLOR.items():
        if source in set(used["source"]):
            axes[0].scatter([], [], c=color, label=source)
    axes[0].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def start_speed(raw: pd.DataFrame, track: pd.DataFrame, path) -> None:
    """Per case: the filter's ground speed against the speed the plots report, over the first 30 seconds of the track. A track
    that starts knowing nothing about its velocity shows a large miss here."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.set_title("largest |filter speed - reported speed| in the first 30 s of each case's track, kt (log)")
    misses = []
    for case, t in track.groupby("case"):
        t = t.sort_values("position_us")
        first = t[t["position_us"] <= t["position_us"].iloc[0] + 30_000_000]
        reported = raw[(raw["case"] == case) & (raw["state"] == "used")].set_index("position_us")["ground_speed_kt"]
        joined = first.join(reported.rename("reported_kt"), on="position_us")
        misses.append((case, float((joined["ground_speed_kt"] - joined["reported_kt"]).abs().max())))
    cases_, values = zip(*misses)
    ax.bar(cases_, np.maximum(values, 1), color="#3987e5", linewidth=0)
    ax.set_yscale("log"); ax.tick_params(axis="x", labelrotation=90, labelsize=7); ax.set_ylabel("kt (log)")
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)
