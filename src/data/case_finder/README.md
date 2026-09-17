# Case finder

Finds moments where today's fusion output looks wrong, lets you look at each one on a map, and lets you mark it as a good test case or not. The approved cases are the list we later use to pull raw plots for the experiment pipeline (TS-1875).

Everything runs on your laptop. The only thing that touches a live system is a read query against BigQuery, and every query is dry run first so you see the cost before it runs.

## The idea

We cannot find interesting cases in the raw plots, because nothing has gone wrong in the raw data yet. The mistakes appear in the output of the current fusion. So we scan one UTC day of fused output for things that cannot be true, such as a track that moves faster than any aircraft can fly, take the strongest hits, and pull the fused plots around each one so you can judge it by eye.

Reviewing takes a few minutes per day of data. Pulling the raw plots for the approved cases is the expensive part, about 5 dollars per day, so it pays to only do that for cases you actually want.

## How to run

You need the `bq` command line tool logged in, with `flyways-aws-dev` as the billing project. Python 3, no packages to install.

```bash
# 1. find cases for one day (about 0.05 dollars)
python3 find_cases.py --day 2026-09-16

# 2. pull the fused plots inside each case box so you can view them (about 0.10 dollars)
python3 pull_case_plots.py --day 2026-09-16

# 3. open the review page
python3 review_server.py --day 2026-09-16
```

Add `--dry-run` to step 1 or 2 to only see the cost. Step 1 keeps marks you already made if you rerun it for the same day. `find_cases.py --from-hits` rebuilds the case list from the saved hits without asking BigQuery again, useful after changing the merge or cap settings.

The review page opens at http://localhost:8765. Pick a case on the left, read why it was picked on the right, play the time slider, and press `g` for a good case or `b` for not interesting. Marks are saved straight into `out/<day>/cases.json`.

The bar under the map has two dropdowns. "Colour by" switches between track id, source, aircraft (hex, else tail, else track id), callsign, altitude, delay until the row was written, and rewritten or not. "Other traffic" shows the surrounding aircraft in grey, in the same colours as the suspect, or hides them. Hollow plots were later rewritten by regular fusion. Red rings mark where a rule fired.

## What the rules look for

Each rule compares a fused plot with the previous plot of the same track. The number in brackets is how often it fired on 2026-09-16, which only had data until 09:00 UTC.

| Rule | What it catches | Fired |
|---|---|---|
| Impossible jump | Consecutive plots imply more than 1,500 kt and at least 2 km apart. Two aircraft glued together, or a wrong position from one source. | 1,750 |
| Hex moved to another track | The same hex address shows up under a different track id within 10 minutes. The current system changed its mind about which aircraft the reports belong to. Ranked by how far the hex jumped. | 127,948 |
| Past rewritten by regular fusion | Plots replaced by a rewrite more than 10 minutes after their own time, 20 or more in one ten minute block of one track. Append fusion first emitted something that regular fusion later changed. | 79,362 |
| Altitude spike | More than 10,000 ft per minute and at least 2,000 ft between consecutive plots. Ranked by feet changed. | 12,289 |
| Gap, then reappeared too far away | No plot for more than 10 minutes, then the track reappears where getting there would have needed more than 650 kt. | 137 |
| Sources disagree, track zigzags | Three plots within 30 s, the middle one from a different source and more than 300 m off the line between its neighbours. | 495 |

A case id is built from the rule, the track id and the time of the first hit, for example `jump-AIR.11208-002024`, so reruns never rename a case and marks stay attached. Hits closer than 0.3 degrees and 10 minutes to each other are merged into one case. At most 10 cases per rule and 2 per track per rule are kept, strongest first, so one broken aircraft cannot fill the whole list. Each case gets a box of 0.3 degrees around the hits and 10 minutes either side.

The recorrelation count is high because the rule fires on every hex that switches track, and that includes routine handovers. The ranking by distance puts the clearly wrong ones first. The counts are there so you know how rare or common a kind of failure is, not because every hit is a case.

## What data is pulled and where it comes from

Both scripts read one table, `flyways.uni_track_provider.fused_plots_aws`. This is the output of the current correlation and fusion services, one row per fused plot, as the rest of the company sees it. It is partitioned by day on `position_timestamp` and clustered by track id, hex and flight plan id. Two columns matter for us beyond the position itself. `track_identifier` is the fused track id, for example `AIR.2007608`. `valid_to` is filled in when a later rewrite by regular fusion replaced the row. Rows with `valid_to` set are the old version of a plot, and the review page draws them hollow.

`find_cases.py` reads about 11 columns for the whole day, 8.5 GB on 2026-09-16. `pull_case_plots.py` reads the same columns plus heading, track angle, tail number and flight plan id, but only for rows inside the case boxes, 15 GB. BigQuery charges by columns read over the day partition, not by rows matched, so the box filter does not lower the price much. That is fine at these sizes.

The tracks that the rule fired on come at full resolution from anywhere in the time window, also outside the box, so the far end of a jump is visible when you zoom out. Inside the box every other track is pulled too. Other tracks are thinned to one plot per 10 seconds so the page stays fast. The right panel summarises what was pulled: how many plots, from which sources, altitude and speed range, whether it is on the ground, how many were rewritten, how many were written to the table more than an hour after their position time, and how much other traffic is in the box. Under it, two charts show altitude and speed of the suspect over the window, one dot per plot in the map colours, hollow when later rewritten, with the moments a rule fired as dashed red lines and the slider time as a lime line. Hover a dot for its value. Timestamps are exported as whole microseconds, because the `bq` JSON export rounds real timestamps down to whole seconds.

## Files

```
find_cases.py        detection query, merge into cases, write reasons
pull_case_plots.py   fused plots per case box, one file per case
review_server.py     tiny local server, serves the page and saves marks
review.html          the review page (deck.gl + MapLibre, OpenFreeMap tiles)
bq.py                runs bq with a dry run and a cost line first
sql/detect.sql       the six rules, {day} filled in by find_cases.py
out/<day>/
  hits.json          every hit BigQuery returned, before merging
  cases.json         the cases, with reason, box, time window, mark and note
  case_plots.sql     the exact query used for the plots
  cases/<id>.json    fused plots for one case
```

`out/` is not committed. The plots are cheap to pull again and the marks live in `cases.json`, which you can copy somewhere safe once a day is reviewed.

## Things to know

- The fused table lags behind. On 2026-09-17 the partition for 2026-09-16 stopped at 09:00 UTC. Check the time range before treating a day as complete.
- Cases lean towards today's failures, because that is what the rules look for. Mix in a few ordinary, well-behaved windows from the same day before using the set to score a new pipeline, otherwise a new approach can look good on the hard cases and quietly break the easy ones.
- The rules and thresholds are a first guess. If a rule keeps producing boring cases, change its threshold or its ranking in `sql/detect.sql` and rerun step 1. It costs 5 cents.
- Next step, not built yet: read the approved cases from `cases.json` and pull the raw plots for them from each source table with one scan per source, about 5 dollars per day.
