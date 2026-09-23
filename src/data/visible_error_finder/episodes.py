"""Step 2: group events into episodes, name what went wrong, score how easy it is to see, pick candidates.

usage: uv run data/visible_error_finder/episodes.py --day 2026-09-22 [--pool 3] [--set regular_spikes]

Reads out/<day>/events_append.parquet and events_regular.parquet, writes out/<day>/candidates.parquet
and candidates.csv. Run from src/.
"""
import argparse, math, pathlib

import numpy as np
import pandas as pd

from sets import SETS, path

HERE = pathlib.Path(__file__).parent
KNOTS = 0.514444           # metres per second in one knot
EPISODE_GAP_S = 90         # events of one track closer than this belong to one episode
WINDOW_S = 600             # candidate window either side of the event
SOURCE_NAME = {1: "TFMS TI", 2: "TFMS OR", 3: "PlaneFinder", 4: "ADS-B Exchange", 5: "Alaska ACARS", 6: "United",
               7: "Spire", 8: "UDL", 9: "MEIS", 10: "STDDS", 11: "uAvionix", 12: "FAA ADS-B EDP", 13: "Aireon"}


def metres(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * np.arcsin(np.sqrt(np.minimum(a, 1)))


def off_line_m(lat, lon, lat_a, lon_a, lat_b, lon_b):
    """Distance of a point from the straight segment a-b, flat earth, fine for a few hundred km."""
    k = math.cos(math.radians(lat_a))
    px, py = (lon - lon_a) * k * 111320, (lat - lat_a) * 111320
    bx, by = (lon_b - lon_a) * k * 111320, (lat_b - lat_a) * 111320
    length2 = bx * bx + by * by
    u = 0 if length2 == 0 else max(0, min(1, (px * bx + py * by) / length2))
    return math.hypot(px - u * bx, py - u * by)


def split_episodes(events: pd.DataFrame) -> pd.DataFrame:
    events = events.sort_values(["fusion", "tid", "t"]).copy()
    new = (events.fusion != events.fusion.shift()) | (events.tid != events.tid.shift()) | (events.t - events.t.shift() > EPISODE_GAP_S)
    events["episode"] = new.cumsum()
    return events


def describe_position(group: pd.DataFrame) -> dict:
    """Spike, teleport or flip-flop, and how far the track left the path."""
    jumps = group[group.kind == "position_jump"].sort_values("t")
    first, last = jumps.iloc[0], jumps.iloc[-1]
    speed = max(float(jumps.gs.max() or 0), float(jumps.pgs.max() or 0)) * KNOTS
    # where the aircraft was before the first jump and after the last one
    before, after = (first.plat, first.plon), (last.lat, last.lon)
    flown = metres(*before, *after)
    expected = speed * (last.t - first.pt)
    returned = len(jumps) >= 2 and flown <= expected + 2000 + 0.3 * expected
    if returned:
        # the plot farthest from the path is where the spike points
        offsets = [off_line_m(r.lat, r.lon, *before, *after) for r in jumps.iloc[:-1].itertuples()]
        excursion = max(offsets)
        biggest = jumps.iloc[int(np.argmax(offsets))]
    else:
        excursion = float(jumps["size"].max())
        biggest = jumps.loc[jumps["size"].idxmax()]
    if len(jumps) >= 6:
        kind = "flip-flop"
    elif returned:
        kind = "position spike"
    else:
        kind = "teleport"
    # visible on a map when the error is large next to the distance flown in a minute
    visibility = excursion / (speed * 60 + 1000)
    return dict(kind=kind, size=excursion, visibility=visibility, at=biggest, jumps=len(jumps),
                summary=f"{kind}: {excursion / 1000:.1f} km off the path, {len(jumps)} jumps in {last.t - first.pt:.0f} s, "
                        f"at {speed / KNOTS:.0f} kt")


def describe_other(group: pd.DataFrame, kind_group: str) -> dict:
    rows = group[group.kind_group == kind_group]
    biggest = rows.loc[rows["size"].idxmax()]
    sources = f"{SOURCE_NAME.get(int(biggest.psrc), biggest.psrc)} to {SOURCE_NAME.get(int(biggest.src), biggest.src)}"
    if kind_group.startswith("altitude"):
        # a spike leaves the altitude before the first jump and comes back to it after the last one
        ordered = rows.sort_values("t")
        before, after = ordered.palt.iloc[0], ordered.alt.iloc[-1]
        peak = float((ordered.alt - before).abs().max())
        if len(ordered) >= 2 and abs(after - before) <= max(500, 0.25 * peak):
            farthest = ordered.loc[(ordered.alt - before).abs().idxmax()]
            return dict(kind="altitude spike", size=peak, visibility=peak / 3000, at=farthest, jumps=len(rows),
                        summary=f"altitude spike: {before:.0f} ft to {farthest.alt:.0f} ft and back to {after:.0f} ft "
                                f"in {ordered.t.iloc[-1] - ordered.pt.iloc[0]:.0f} s, {sources}, {len(rows)} jumps")
        name = "uAvionix altitude" if kind_group.endswith("uavionix") else "altitude jump"
        return dict(kind=name, size=biggest["size"], visibility=biggest["size"] / 3000, at=biggest, jumps=len(rows),
                    summary=f"{name}: {biggest.palt:.0f} ft to {biggest.alt:.0f} ft in {biggest["dt"]:.1f} s, {sources}, {len(rows)} jumps")
    if kind_group.startswith("speed"):
        name = "uAvionix speed" if kind_group.endswith("uavionix") else "speed jump"
        return dict(kind=name, size=biggest["size"], visibility=biggest["size"] / 200, at=biggest, jumps=len(rows),
                    summary=f"{name}: {biggest.pgs:.0f} kt to {biggest.gs:.0f} kt in {biggest["dt"]:.1f} s, {sources}, {len(rows)} jumps")
    # sharp turn: the shorter leg of the turn, next to the distance flown in a minute
    leg = min(biggest.dist_m, biggest.next_dist_m)
    speed = max(float(biggest.gs or 0), float(biggest.pgs or 0)) * KNOTS
    return dict(kind="sharp turn", size=biggest["size"], visibility=leg / (speed * 60 + 1000) * biggest["size"] / 180,
                at=biggest, jumps=len(rows),
                summary=f"sharp turn: {biggest['size']:.0f} degrees with legs of {biggest.dist_m / 1000:.1f} and "
                        f"{biggest.next_dist_m / 1000:.1f} km at {speed / KNOTS:.0f} kt, {sources}, {len(rows)} turns")


def describe(events: pd.DataFrame) -> pd.DataFrame:
    """One row per episode and kind of error in it."""
    rows = []
    for _, group in events.groupby("episode"):
        found = []
        if (group.kind == "position_jump").any():
            found.append(describe_position(group))
        for kind_group in ("altitude_jump", "altitude_jump_uavionix", "speed_jump", "speed_jump_uavionix", "sharp_turn"):
            # turns that belong to a position jump are the same error seen twice
            if kind_group == "sharp_turn" and (group.kind == "position_jump").any():
                continue
            if (group.kind_group == kind_group).any():
                found.append(describe_other(group, kind_group))
        for item in found:
            at = item.pop("at")
            rows.append(dict(item, fusion=at.fusion, tid=at.tid, hex=at.hex, cs=at.cs, t_event=at.t, lat=at.lat, lon=at.lon, plat=at.plat, plon=at.plon,
                             alt=at.alt, gs=at.gs, src=at.src, psrc=at.psrc, track_plots=at.track_plots))
    return pd.DataFrame(rows)


def score(episodes: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Big error, calm track around it, a bit more for the US."""
    # other events of the same track within the window make the picture messy
    counts = []
    by_track = {key: group.t.values for key, group in events.groupby(["fusion", "tid"])}
    for e in episodes.itertuples():
        times = by_track[(e.fusion, e.tid)]
        counts.append(int(((times > e.t_event - WINDOW_S) & (times < e.t_event + WINDOW_S)).sum()))
    episodes["events_in_window"] = counts
    calm = 1 / (1 + np.maximum(episodes.events_in_window - episodes.jumps, 0) / 5)
    us = ((episodes.lon.between(-170, -50)) & (episodes.lat.between(15, 72))).map({True: 1.2, False: 1.0})
    episodes["score"] = np.log1p(episodes.visibility) * calm * us
    return episodes


def pick(episodes: pd.DataFrame, day: str, pool: int, quota: dict) -> pd.DataFrame:
    """Best per kind, one per track and kind, then merge append and regular for the same moment."""
    episodes = episodes.sort_values("score", ascending=False)
    # the same error in append and regular fusion is one candidate
    episodes["minute"] = (episodes.t_event // 300).astype(int)
    merged = (episodes.groupby(["tid", "kind", "minute"], sort=False)
              .agg(fusion=("fusion", lambda f: "both" if f.nunique() > 1 else f.iloc[0]),
                   **{c: (c, "first") for c in episodes.columns if c not in ("tid", "kind", "minute", "fusion")})
              .reset_index())
    merged = merged.sort_values("score", ascending=False).drop_duplicates(["tid", "kind"])
    # half slow aircraft, half fast ones, so airliners at cruise are not crowded out
    fast = merged.gs.fillna(0) >= 200
    chosen = pd.concat([pd.concat([merged[(merged.kind == kind) & ~fast].head(n // 2),
                                   merged[(merged.kind == kind) & fast].head(n - n // 2)])
                        for kind, n in ((kind, n * pool) for kind, n in quota.items())])
    # at most two candidates per track
    chosen = chosen.sort_values("score", ascending=False).groupby("tid").head(2)
    day_start = pd.Timestamp(day, tz="UTC").timestamp()
    chosen["t0"] = np.maximum(chosen.t_event - WINDOW_S, day_start)
    chosen["t1"] = np.minimum(chosen.t_event + WINDOW_S, day_start + 86400 - 0.001)
    chosen["who"] = chosen.cs.fillna("") + "  hex " + chosen.hex.fillna("?") + "  track " + chosen.tid
    chosen["id"] = [f"{k.replace(' ', '_').replace('-', '_')}-{t}-{pd.Timestamp(s, unit='s'):%H%M%S}"
                    for k, t, s in zip(chosen.kind, chosen.tid, chosen.t_event)]
    chosen["summary"] = chosen.summary + ", seen in " + chosen.fusion.map({"both": "append and regular fusion"}).fillna(chosen.fusion + " fusion only")
    return chosen.reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--pool", type=int, default=3, help="pick this many times the quota; check.py drops the thin ones")
    parser.add_argument("--set", default="", choices=SETS)
    args = parser.parse_args()
    chosen_set = SETS[args.set]
    out = HERE / "out" / args.day

    # events of both tables, in the air, with a known track
    events = pd.concat([pd.read_parquet(out / f"events_{f}.parquet").assign(fusion=f)
                        for f in chosen_set["fusions"] if (out / f"events_{f}.parquet").exists()])
    # saved results from before next_dist_m was a column
    events["next_dist_m"] = metres(events.lat, events.lon, events.nlat, events.nlon)
    events = split_episodes(events)

    # what went wrong in each episode and how visible it is
    episodes = score(describe(events), events)
    episodes.to_parquet(path(out, "episodes", args.set))

    # the candidates to draw
    chosen = pick(episodes, args.day, args.pool, chosen_set["quota"])
    chosen.to_parquet(path(out, "candidates", args.set))
    chosen.to_csv(path(out, "candidates", args.set, ".csv"), index=False)
    print(episodes.kind.value_counts().to_string())
    print(f"{len(chosen)} candidates:")
    print(chosen.kind.value_counts().to_string())


if __name__ == "__main__":
    main()
