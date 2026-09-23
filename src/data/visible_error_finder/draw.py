"""Step 4: one picture per candidate: map of append and regular fusion, altitude and speed over time.

usage: uv run data/visible_error_finder/draw.py --day 2026-09-22 [--only <candidate id>] [--set regular_spikes]

Reads out/<day>/checked.parquet and plots.parquet, writes out/<day>/pictures/<id>.png. Run from src/.
"""
import argparse, math, pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sets import SETS, path

HERE = pathlib.Path(__file__).parent
SOURCE_NAME = {1: "TFMS TI", 2: "TFMS OR", 3: "PlaneFinder", 4: "ADS-B Exchange", 5: "Alaska ACARS", 6: "United",
               7: "Spire", 8: "UDL", 9: "MEIS", 10: "STDDS", 11: "uAvionix", 12: "FAA ADS-B EDP", 13: "Aireon"}
SOURCE_COLOUR = {4: "#1f77b4", 3: "#ff7f0e", 11: "#2ca02c", 1: "#9467bd", 2: "#8c564b", 10: "#e377c2",
                 6: "#17becf", 5: "#bcbd22", 13: "#7f7f7f"}
MAP_SECONDS = 150          # map shows this much time either side of the event
FUSION_STYLE = {"append": dict(marker="o", ms=3), "regular": dict(marker="s", ms=3)}


def implied_speed_kt(track: pd.DataFrame) -> np.ndarray:
    """Speed the positions themselves imply between consecutive plots."""
    lat, lon, t = np.radians(track.lat.values), np.radians(track.lon.values), track.t.values
    dlat, dlon = np.diff(lat), np.diff(lon)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2) ** 2
    metres = 2 * 6371000 * np.arcsin(np.sqrt(a))
    seconds = np.maximum(np.diff(t), 0.2)
    return np.concatenate([[np.nan], metres / seconds / 0.514444])


def draw_map(ax, track: pd.DataFrame, candidate, title: str):
    near = track[(track.t - candidate.t_event).abs() <= MAP_SECONDS]
    if near.empty:
        ax.set_title(f"{title}: no plots"); ax.axis("off"); return
    ax.plot(track.lon, track.lat, "-", color="#bbbbbb", lw=0.8, zorder=1)
    for src, group in near.groupby("src"):
        ax.plot(group.lon, group.lat, "o", ms=3.5, color=SOURCE_COLOUR.get(src, "black"),
                label=SOURCE_NAME.get(src, str(src)), zorder=2)
    ax.plot(candidate.lon, candidate.lat, "o", ms=18, mfc="none", mec="red", mew=1.5, zorder=3)
    # frame the plots near the event and both ends of the jump, same scale in both directions
    lats = pd.concat([near.lat, pd.Series([candidate.lat, candidate.plat])]).dropna()
    lons = pd.concat([near.lon, pd.Series([candidate.lon, candidate.plon])]).dropna()
    middle_lat, middle_lon = (lats.min() + lats.max()) / 2, (lons.min() + lons.max()) / 2
    squash = math.cos(math.radians(middle_lat))
    half = max(lats.max() - lats.min(), (lons.max() - lons.min()) * squash) * 0.55 + 0.005
    ax.set_xlim(middle_lon - half / squash, middle_lon + half / squash)
    ax.set_ylim(middle_lat - half, middle_lat + half)
    ax.set_aspect(1 / squash, adjustable="box")
    ax.set_title(f"{title}, {len(near)} plots within {MAP_SECONDS} s", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc="best")


def draw_chart(ax, tracks: dict, candidate, column: str, label: str):
    for fusion, track in tracks.items():
        if track.empty:
            continue
        minutes = (track.t - candidate.t_event) / 60
        values = implied_speed_kt(track) if column == "implied" else track[column].values
        colours = [SOURCE_COLOUR.get(s, "black") for s in track.src]
        ax.scatter(minutes, values, s=6 if fusion == "append" else 10, c=colours,
                   marker=FUSION_STYLE[fusion]["marker"], alpha=0.8 if fusion == "append" else 0.5,
                   label=fusion, edgecolors="none")
    ax.axvline(0, color="red", lw=0.8, ls="--")
    ax.set_ylabel(label, fontsize=8)
    ax.set_xlabel("minutes from event", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=7, loc="best", markerscale=2)


def main_track(plots: pd.DataFrame, candidate) -> pd.DataFrame:
    """The candidate's own track, or in the other table the track of the same hex nearest the event."""
    own = plots[plots.tid == candidate.tid]
    if not own.empty:
        return own.sort_values("t")
    near = plots[(plots.t - candidate.t_event).abs() <= MAP_SECONDS]
    if near.empty:
        return near
    return plots[plots.tid == near.tid.value_counts().index[0]].sort_values("t")


def draw(candidate, plots: pd.DataFrame, path: pathlib.Path):
    tracks = {f: main_track(plots[plots.fusion == f], candidate) for f in ("append", "regular")}
    fig = plt.figure(figsize=(14, 9))
    grid = fig.add_gridspec(2, 3, height_ratios=[1.5, 1])
    for column, fusion in enumerate(("append", "regular")):
        track = tracks[fusion]
        name = f"{fusion} fusion, track {track.tid.iloc[0]}" if not track.empty else f"{fusion} fusion"
        draw_map(fig.add_subplot(grid[0, column]), track, candidate, name)
    draw_chart(fig.add_subplot(grid[0, 2]), tracks, candidate, "implied", "speed from positions (kt)")
    draw_chart(fig.add_subplot(grid[1, 0]), tracks, candidate, "alt", "altitude (ft)")
    draw_chart(fig.add_subplot(grid[1, 1]), tracks, candidate, "gs", "reported ground speed (kt)")
    draw_chart(fig.add_subplot(grid[1, 2]), tracks, candidate, "trk", "reported track angle (deg)")
    fig.suptitle(f"{candidate.id}   {candidate.who}\n{candidate.summary}", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--only")
    parser.add_argument("--set", default="", choices=SETS)
    args = parser.parse_args()
    out = HERE / "out" / args.day
    candidates = pd.read_parquet(path(out, "checked", args.set))
    plots = pd.read_parquet(path(out, "plots", args.set))
    by_id = dict(tuple(plots.groupby("id")))
    pictures = path(out, "pictures", args.set, "")
    pictures.mkdir(exist_ok=True)
    for candidate in candidates.itertuples():
        if args.only and candidate.id != args.only:
            continue
        draw(candidate, by_id.get(candidate.id, plots.iloc[:0]), pictures / f"{candidate.id}.png")
    print(f"drew {len(candidates)} pictures into {pictures}")


if __name__ == "__main__":
    main()
