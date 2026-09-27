# Experiment loop harness

A tiny harness for the Kalman experiment loop (agent-office task kalman-experiment-loop). It runs the normalizer and the Kalman
strategy on the suspect aircraft of every case in `data/cases/` (only that hex, so all 34 cases take about 25 seconds), draws one
picture per case and a few cross-case evidence figures, and writes them with a summary table to the task folder in
`~/agent-office/tasks/kalman-experiment-loop/research/iterNN/`. Nothing is written into the case folders.

```bash
# from src/, with the main repo's venv (the worktree has none)
../../track_quality_and_state_estimation/.venv/bin/python -m experiments.loop --iteration 5 --against 4 --note "what this tries" [--case fw20] [--param gate_sigmas=6]
```

`cases.py` loads a case's suspect plots and production tracks (cached as a pickle under `experiments/cache/`; delete the cache when the
normalizer's inputs change). `run.py` runs one case and computes the summary numbers. `draw.py` draws the per-case picture, `evidence.py`
the cross-case figures, `loop.py` ties it together and writes the gallery.
