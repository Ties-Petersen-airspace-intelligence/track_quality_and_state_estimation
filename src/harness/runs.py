"""Bookkeeping for runs: where a run lives, its automatic label, and the manifest that says what produced it.

A run is one strategy applied to one case once, stored in <case>/runs/<strategy>/<label>/. Its run.json
records the strategy, the label, the batch it belongs to, the git commit of this repo at the time, the
strategy's parameters, a free note, and a few counts of what came out. Labels are r001, r002, ... per
strategy per case, so nothing is ever overwritten. A batch is one invocation of a command, shared by every
run it produced, so the same code run on four cases can be found again as one group.
"""
from __future__ import annotations

import datetime as dt
import json, pathlib, re, shlex, subprocess, sys

LABEL = re.compile(r"^r(\d{3,})$")


def case_folders(paths: list[str]) -> list[pathlib.Path]:
    """Each path is a case folder (has case.json) or a folder of case folders; in either case, the cases."""
    out = []
    for p in paths:
        p = pathlib.Path(p)
        if (p / "case.json").exists():
            out.append(p)
        elif p.is_dir():
            out += sorted(q for q in p.iterdir() if (q / "case.json").exists())
        else:
            raise SystemExit(f"not a case or a folder of cases: {p}")
    return out


def git_info() -> dict:
    """Commit, branch and whether the working tree had uncommitted changes. Empty when git is not around."""
    try:
        here = pathlib.Path(__file__).parent
        run = lambda *args: subprocess.run(["git", *args], cwd=here, capture_output=True, text=True, check=True).stdout.strip()
        return dict(commit=run("rev-parse", "HEAD"), branch=run("rev-parse", "--abbrev-ref", "HEAD"), dirty=bool(run("status", "--porcelain")))
    except Exception:
        return {}


def new_batch() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def next_label(case: pathlib.Path, strategy: str) -> str:
    """The next free label for a strategy in this case."""
    folder = case / "runs" / strategy
    taken = [int(m.group(1)) for p in folder.glob("r*") if (m := LABEL.match(p.name))] if folder.exists() else []
    return f"r{(max(taken) + 1 if taken else 1):03d}"


def new_run(case: pathlib.Path, strategy: str, label: str) -> pathlib.Path:
    """A fresh, empty run folder runs/<strategy>/<label>/."""
    folder = case / "runs" / strategy / label
    folder.mkdir(parents=True)
    return folder


def write_manifest(folder: pathlib.Path, strategy: str, label: str, batch: str, case: pathlib.Path, *, params: dict, note: str, counts: dict, duration_s: float, git: dict) -> dict:
    manifest = dict(
        strategy=strategy, label=label, batch=batch, case=case.name,
        created=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), duration_s=round(duration_s, 1),
        command=shlex.join(["uv", "run", "-m", module_name(sys.argv[0]), *sys.argv[1:]]),
        git=git, params=params, note=note, counts=counts,
    )
    (folder / "run.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def module_name(script: str) -> str:
    """harness/run.py -> harness.run, so the command in the manifest can be pasted back."""
    p = pathlib.Path(script)
    parts = list(p.with_suffix("").parts)
    return ".".join(parts[parts.index("harness"):]) if "harness" in parts else p.stem


def list_runs(case: pathlib.Path) -> list[dict]:
    """Every run of the case that has output, oldest first, each with its manifest and an id 'strategy/label'."""
    out = []
    root = case / "runs"
    if not root.exists():
        return out
    for strategy in sorted(p for p in root.iterdir() if p.is_dir()):
        for folder in sorted(p for p in strategy.iterdir() if p.is_dir() and (p / "fused_plots.parquet").exists() and (p / "raw_plots.parquet").exists()):
            manifest = json.loads((folder / "run.json").read_text()) if (folder / "run.json").exists() else dict(strategy=strategy.name, label=folder.name)
            out.append(dict(id=f"{strategy.name}/{folder.name}", **manifest))
    return out


def set_note(case: pathlib.Path, strategy: str, label: str, note: str) -> dict:
    path = case / "runs" / strategy / label / "run.json"
    manifest = json.loads(path.read_text())
    manifest["note"] = note
    path.write_text(json.dumps(manifest, indent=1))
    return manifest
