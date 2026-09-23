"""Step 3b: drop candidates whose track is too thin to show, keep the best per kind for drawing.

usage: uv run data/visible_error_finder/check.py --day 2026-09-22 [--set regular_spikes]

Reads out/<day>/candidates.parquet and plots.parquet, writes out/<day>/checked.parquet. Run from src/.
"""
import argparse, pathlib

import pandas as pd

from sets import SETS, path

HERE = pathlib.Path(__file__).parent
SIDE_S = 300              # look this far before and after the event
MIN_PLOTS_PER_SIDE = 25   # a track with fewer plots on either side is not worth showing
MIN_WITH_ALTITUDE = 0.8   # share of plots near the event that must have an altitude


def plots_around(candidate, plots: pd.DataFrame) -> tuple[int, int]:
    own = plots[plots.tid == candidate.tid]
    before = ((own.t < candidate.t_event) & (own.t >= candidate.t_event - SIDE_S)).sum()
    after = ((own.t > candidate.t_event) & (own.t <= candidate.t_event + SIDE_S)).sum()
    return int(before), int(after)


def altitude_share(candidate, plots: pd.DataFrame) -> float:
    """Tracks without altitude look odd in Flyways."""
    own = plots[(plots.tid == candidate.tid) & ((plots.t - candidate.t_event).abs() <= SIDE_S)]
    return float(own.alt.notna().mean()) if len(own) else 0.0


def balanced(rows: pd.DataFrame, fast: pd.Series, n: int) -> pd.DataFrame:
    """Half slow and half fast aircraft, the rest filled from whichever has more."""
    chosen = pd.concat([rows[~fast].head(n // 2), rows[fast].head(n - n // 2)])
    rest = rows.drop(chosen.index).head(n - len(chosen))
    return pd.concat([chosen, rest])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--set", default="", choices=SETS)
    args = parser.parse_args()
    out = HERE / "out" / args.day
    candidates = pd.read_parquet(path(out, "candidates", args.set))
    plots = pd.read_parquet(path(out, "plots", args.set))
    by_id = dict(tuple(plots.groupby("id")))

    # enough plots on both sides of the event
    sides = [plots_around(c, by_id.get(c.id, plots.iloc[:0])) for c in candidates.itertuples()]
    candidates["plots_before"] = [b for b, _ in sides]
    candidates["plots_after"] = [a for _, a in sides]
    candidates["with_altitude"] = [altitude_share(c, by_id.get(c.id, plots.iloc[:0])) for c in candidates.itertuples()]
    thick = candidates[(candidates.plots_before >= MIN_PLOTS_PER_SIDE) & (candidates.plots_after >= MIN_PLOTS_PER_SIDE)
                       & (candidates.with_altitude >= MIN_WITH_ALTITUDE)]

    # best of each kind, half slow and half fast as in episodes.py
    thick = thick.sort_values("score", ascending=False)
    fast = thick.gs.fillna(0) >= 200
    checked = pd.concat([balanced(thick[thick.kind == kind], fast[thick.kind == kind], n)
                         for kind, n in SETS[args.set]["quota"].items()])
    checked.reset_index(drop=True).to_parquet(path(out, "checked", args.set))
    print(f"{len(candidates)} candidates, {len(thick)} with {MIN_PLOTS_PER_SIDE}+ plots on both sides and altitudes, {len(checked)} to draw")
    print(checked.kind.value_counts().to_string())


if __name__ == "__main__":
    main()
