"""Run one strategy on one case and store what it produced.

usage: uv run -m harness.run --case data/cases/<name> --strategy baseline [--note "..."]
       uv run -m harness.run --case data/cases --strategy baseline      # every case in the folder

Each raw plot, in the order we received it, goes through three steps: the normalizer turns it into a Measurement or removes it
(normalization/), the strategy answers the Measurement with a StrategyResult and maybe a TrackUpdate (strategy.py), and at the
end the output layer writes the files (output.py) to <case>/runs/<strategy>/<label>/, a fresh folder every time (labels r001,
r002, ...), next to run.json, which says what produced the run (see runs.py).
"""
from __future__ import annotations

import argparse, pathlib, time

from .raw_plots import load_case
from .normalization.basic import Basic
from .strategies.baseline import Baseline
from .strategies.kalman import Kalman
from . import output, runs

STRATEGIES = {"baseline": Baseline, "kalman": Kalman}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, nargs="+", help="case folder(s), or a folder that holds case folders")
    ap.add_argument("--strategy", required=True, choices=sorted(STRATEGIES))
    ap.add_argument("--note", default="", help="free text stored with the run")
    a = ap.parse_args()
    batch, git = runs.new_batch(), runs.git_info()
    for case in runs.case_folders(a.case):
        run_one(case, a.strategy, a.note, batch, git)


def run_one(case: pathlib.Path, name: str, note: str, batch: str, git: dict) -> None:
    started = time.time()

    # load the raw plots in receipt order
    plots = load_case(case)
    print(f"{case.name}: {len(plots)} raw plots loaded in {time.time() - started:.1f} s")

    # normalize each plot; give what is kept to the strategy; keep what happened to every plot and every track update
    normalizer, strategy = Basic(), STRATEGIES[name]()
    t0 = time.time()
    raw_rows, updates = [], []
    for plot in plots:
        normalized = normalizer.normalize(plot)
        result = strategy.update(normalized.measurement) if normalized.measurement else None
        raw_rows.append(output.raw_plot_row(plot, normalized, result))
        if result and result.update:
            updates.append((plot.received_us, result.update))
    print(f"  {len(updates)} track updates in {time.time() - t0:.1f} s")
    if not updates:
        print("  no track updates, no run written")
        return

    # store the fused plots, what happened to each raw plot, and the strategy's numbers about its tracks
    out = runs.new_run(case, name, runs.next_label(case, name))
    fused, raw = output.write(out, raw_rows, updates)

    # what produced it, and a few counts
    removed = raw[raw["state"] == "removed"]
    normalization = dict(name=normalizer.name, params=normalizer.params, counts=dict(kept=len(raw) - len(removed), removed=len(removed),
                                                                                  reasons=removed["reason"].value_counts().to_dict()))
    counts = dict(raw_plots=len(plots), updates=len(updates), fused_plots=len(fused), tracks=int(fused["track_id"].nunique()), rewritten=int(fused["valid_to"].notna().sum()),
                  outcomes=raw["state"].value_counts().to_dict(), reasons=raw.loc[raw["reason"] != "", "reason"].value_counts().to_dict())
    runs.write_manifest(out, name, out.name, batch, case, params=dict(strategy.params), normalization=normalization, note=note, counts=counts,
                        duration_s=time.time() - started, git=git)
    print(f"  {len(fused)} fused plots written to {out}; raw plots " + ", ".join(f"{k} {v}" for k, v in counts["outcomes"].items()))


if __name__ == "__main__":
    main()
