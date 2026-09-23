# Visible error finder

Finds moments where production fusion draws a track that is visibly wrong: a spike far off the path, a teleport, a zigzag, an altitude or speed that leaps. The goal is examples that anyone understands by looking at them, for demos and as harness cases. It reads append fusion and regular fusion for whole UTC days.

Everything runs on the laptop. BigQuery is only read, and every query is dry run first so the cost is printed before it runs.

## How to run

From `src/`, with `bq` logged in and `flyways-aws-dev` as billing project:

```bash
uv run data/visible_error_finder/find.py --day 2026-09-21        # 1. steps that look wrong, both tables, about $0.35 per day
uv run data/visible_error_finder/episodes.py --day 2026-09-21    # 2. group into episodes, score, pick about 500 candidates
uv run data/visible_error_finder/pull.py --day 2026-09-21        # 3. plots around each candidate, both tables, about $0.40 per day
(cd data/visible_error_finder && uv run check.py --day 2026-09-21)   # 3b. drop thin tracks, keep about 160
uv run data/visible_error_finder/draw.py --day 2026-09-21        # 4. one picture per candidate
uv run data/visible_error_finder/shortlist.py --ratings <folder>  # 5. merge ratings of the pictures into out/shortlist.json
uv run data/visible_error_finder/review.py                        # 6. review page on http://localhost:8771
```

The review page shows each candidate live: two maps (append and regular fusion, synced, scroll to zoom) with buttons to fit the jump, the path before or after the event, or the whole 20 minutes, and four charts (altitude, reported ground speed, speed from positions, reported track angle) that share one time axis in UTC. Plotly comes from the jsdelivr CDN and the map tiles from Carto, so the page needs internet. Only cards near the screen are drawn, because browsers allow a limited number of map canvases. Marks go to `out/marks.json`.

`--dry-run` on `find.py`, `pull.py` and `flyways.py` only prints the cost.

A named set (`sets.py`) repeats steps 2 to 6 for one fusion and some kinds of error, with its own files (`<stem>_<set>`). The set `regular_spikes` is what Flyways shows: regular fusion, position and altitude spikes that come back. For it, add `--set regular_spikes` to `episodes.py`, `pull.py`, `check.py`, `draw.py` and `shortlist.py`, then:

```bash
uv run data/visible_error_finder/flyways.py --list regular_spikes                  # 7. a Flyways link on every card, about $0.03
uv run data/visible_error_finder/review.py --list regular_spikes --port 8773       # page with links, marks to out/marks_regular_spikes.json
```

The Flyways link opens the ASD app at a snapshot 30 minutes after the event, because it shows the hour before the snapshot. The track is the regular fusion flight plan id valid at the event, else the regular track id (`AIR.<n>`); both work. `find.py --saved append=<table>` reads the result table of an earlier run (BigQuery keeps it 24 hours) instead of scanning again.

## How it decides

1. `sql/steps.sql` compares each plot of a track with the plot before and after it, only for aircraft in the air (at least 60 kt and 500 ft). A step is kept when it is a position jump (at least 1.5 km further than the ground speed allows), an altitude jump (over 1,500 ft and faster than 6,000 ft per minute), a speed jump (reported ground speed changes by more than 120 kt within 20 s) or a sharp turn (direction changes more than 120 degrees at over 100 kt). `sql/keep.sql` cuts that down to the bigger ones.
2. `episodes.py` groups the steps of one track that are less than 90 s apart. A group of position jumps is a spike when the track comes back to where the aircraft should be, a teleport when it does not, and a flip-flop with six or more jumps. The score is how far the track leaves its path next to the distance the aircraft flies in a minute, times a penalty for other odd steps of the same track within 10 minutes, times 1.2 over the US.
3. `check.py` drops candidates with fewer than 25 plots in the 5 minutes before or after, and keeps a quota per kind, half slow aircraft and half fast.
4. The pictures are then looked at one by one and rated on how visible and how clean the error is.

## Things to know

- Append fusion keeps only 7 days (`append_only_plots` expires partitions after 7 days). Regular fusion and the raw source tables have no expiry.
- Append and regular fusion use different track ids. Append uses the hex address, regular uses `AIR.<n>`. The pull matches on either.
- uAvionix causes most altitude jumps (GPS height instead of barometric) and most speed jumps (ground speed in NM/s). Only the biggest 300 of each are kept, so they do not fill the list.
- The regular fusion partition of a day keeps filling for a while after the day ends. On 23 Sep, 22 Sep was a third of the size of 21 Sep.
- `bq` downloads large results slowly, over 10 minutes for a million rows. That is why the SQL filters hard.
- `out/` is not committed.
