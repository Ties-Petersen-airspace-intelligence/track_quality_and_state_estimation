"""One iteration of the experiment loop over every case's suspect aircraft.

usage (from src/, with the main repo's venv):
    python -m experiments.loop --iteration 0 --note "current filter as is" [--against 0] [--case fw04]

Writes to ~/agent-office/tasks/kalman-experiment-loop/research/iterNN/: one PNG per case, summary.csv, an index.html gallery, and when
--against is given, a compare.csv with the numbers of both iterations side by side.
"""
from __future__ import annotations

import argparse, html, json, pathlib, time

import pandas as pd

from . import cases, draw, evidence
from .run import run, numbers

OUT = pathlib.Path.home() / "agent-office" / "tasks" / "kalman-experiment-loop" / "research"
COMPARE_COLUMNS = ["used", "rejected", "median_sigmas", "over_5_sigma_pct", "kalman_max_jump_m", "kalman_max_implied_kt", "kalman_max_alt_step_ft", "kalman_max_speed_kt"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iteration", type=int, required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--against", type=int, default=None, help="earlier iteration to compare the numbers with")
    ap.add_argument("--case", default=None, help="only cases whose folder name contains this")
    ap.add_argument("--hex", default=None, help="one aircraft of the case instead of its suspect (with --case)")
    ap.add_argument("--param", action="append", default=[], help="strategy parameter override name=value")
    ap.add_argument("--normalizer-param", action="append", default=[], help="normalizer parameter override name=value")
    a = ap.parse_args()
    overrides = {k: float(v) for k, v in (p.split("=") for p in a.param)}
    normalizer_overrides = {k: float(v) for k, v in (p.split("=") for p in a.normalizer_param)}

    out = OUT / f"iter{a.iteration:02d}"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    started = time.time()
    for folder in cases.case_folders():
        if a.case and a.case not in folder.name:
            continue
        data = cases.load(folder, a.hex)
        result = run(data, overrides, normalizer_overrides)
        n = numbers(result, data)
        rows.append(n)
        name = short(folder.name) + (f"-{a.hex.upper()}" if a.hex else "")
        draw.draw(data, result, out / f"{name}.png", f"iteration {a.iteration}")
        result["raw"].assign(case=name).to_parquet(out / f"{name}_raw.parquet")
        result["track"].assign(case=name).to_parquet(out / f"{name}_track.parquet")
        print(f"{short(folder.name):10s} used {n['used']:5d} rej {n['rejected']:4d}  >5σ {n.get('over_5_sigma_pct', float('nan')):5.1f}%  "
              f"jump kalman {n['kalman_max_jump_m']:8.0f} m  regular {n['regular_max_jump_m']:8.0f} m  alt step kalman {n['kalman_max_alt_step_ft']:6.0f} ft")
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "summary.csv", index=False)
    (out / "run.json").write_text(json.dumps(dict(iteration=a.iteration, note=a.note, strategy_params=result["params"], normalizer_params=result["normalizer_params"],
                                                  duration_s=round(time.time() - started, 1)), indent=1))
    compare = None
    if a.against is not None:
        before = pd.read_csv(OUT / f"iter{a.against:02d}" / "summary.csv").set_index("case")
        compare = summary.set_index("case")[COMPARE_COLUMNS].join(before[COMPARE_COLUMNS], lsuffix=f"_i{a.iteration}", rsuffix=f"_i{a.against}")
        compare.to_csv(out / "compare.csv")
    evidence.draw_all(out)
    gallery(out, summary, a, compare)
    print(f"done in {time.time() - started:.0f} s -> {out}")


def short(name: str) -> str:
    return name.split("-")[0]


def gallery(out: pathlib.Path, summary: pd.DataFrame, a, compare: pd.DataFrame | None) -> None:
    """A plain page with the summary table and every picture, for looking through an iteration quickly."""
    parts = [f"<html><head><meta charset='utf-8'><title>iteration {a.iteration}</title><style>body{{background:#0a0b0d;color:#c3c8cf;font:13px Menlo,monospace;padding:16px}}"
             "table{border-collapse:collapse}td,th{border:1px solid #24272c;padding:3px 8px;text-align:right}th{color:#fff}td:first-child,th:first-child,td:last-child{text-align:left}"
             "img{width:100%;max-width:1400px;display:block;margin:24px 0}h2{color:#fff;font-weight:500}</style></head><body>",
             f"<h2>iteration {a.iteration}: {html.escape(a.note)}</h2>"]
    columns = ["case", "kind", "used", "skipped", "rejected", "median_sigmas", "over_5_sigma_pct",
               "kalman_max_jump_m", "regular_max_jump_m", "append_max_jump_m", "kalman_max_alt_step_ft", "regular_max_alt_step_ft", "kalman_max_speed_kt", "regular_max_speed_kt", "reasons"]
    parts.append(summary[[c for c in columns if c in summary]].to_html(index=False, na_rep="", float_format=lambda v: f"{v:g}"))
    if compare is not None:
        parts.append(f"<h2>against iteration {a.against}</h2>" + compare.to_html(na_rep="", float_format=lambda v: f"{v:g}"))
    for case in summary["case"]:
        parts.append(f"<h2 id='{short(case)}'>{case}</h2><img src='{short(case)}.png'>")
    (out / "index.html").write_text("\n".join(parts) + "</body></html>")


if __name__ == "__main__":
    main()
