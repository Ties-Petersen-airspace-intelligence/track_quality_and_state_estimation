# Track harness

Replays real raw plots through a tracking strategy and shows the result next to what production did. In the viewer everything that produced fused plots is called a strategy, production included. This is the experiment pipeline of TS-1804: one case, all sources, the dumb baseline first, better strategies later.

Everything runs locally from Parquet files in `src/data/cases/<case>/`. Nothing here talks to a live system.

## Run it

```bash
# from the src folder
uv run -m harness.run --case data/cases/paris-tx-n464ae-2026-09-16 --strategy baseline --note "what this run tries"
uv run -m harness.viewer.server --cases data/cases
```

The first command feeds every raw plot of the case through the normalizer to the strategy and stores what came out under `runs/baseline/r001/`. The second opens the viewer at http://localhost:8770 with every case in the folder in a dropdown at the top. Production needs no command: the viewer reads the two production tables that came with the case and shows them as two more strategies, `prod_fusion_append` for what the append path first emitted and `prod_fusion_regular` for the result after the regular and recorrelation rewrites. `--port` picks another port and `--no-browser` keeps the server from opening a tab.

`--case` also takes a folder of cases, so `--case data/cases` runs the strategy on every case in one go. `--note` is free text kept with the run.

## What is stored where

```
data/cases/<case>/
  case.json, sql/                  what was pulled, where, when, and the queries
  raw/<source>.parquet             the raw plots as pulled, one file per source
  production/append.parquet        production's append table (append_only_plots), as pulled
  production/final.parquet         production's provider table (fused_plots_aws), as pulled
  runs/<strategy>/<label>/         one folder per run: r001, r002, ...; made locally, not committed
    run.json                       what produced the run
    fused_plots.parquet            what the strategy published
    raw_plots.parquet              what the normalizer and the strategy did with each raw plot
    track_state.parquet            the strategy's numbers about its tracks, when it has any
    strategy_state.parquet         the strategy's own state per track row, for looking ahead
```

A raw plot is named by its source and its row number in `raw/<source>.parquet`.

`fused_plots.parquet` has one row per point of every track update the strategy returned: the update's number (column `event`), track id, `created_at` (the received time of the plot that caused the update) and quality (APPEND_ONLY for an append, REGULAR for a rewrite), the update's `since` and `until`, every field of the fused plot under its proto name (the point is written as production's `FusedPlot` message, so names and types match production), and `valid_to`, the `created_at` of the first later update on the same track that covers this plot's position time, empty if none did. The viewer shows a plot when `created_at <= now < valid_to`, so a strategy that rewrites the past is replayed the way consumers would have seen it. Appends and rewrites sit in the same table; the quality column says which is which.

`raw_plots.parquet` has one row per raw plot: source, row, state (`removed` by the normalizer, or `used`, `skipped` or `rejected` by the strategy), track id, reason, and one column per number the strategy gave with that plot. `track_state.parquet` has one row per track point that has numbers: track id, position time, `created_at`, and one column per number. The viewer matches a track state row to the fused plot of the same track and position time.

Numbers of a track point named starting with `state_` are the strategy's own state, for example the Kalman filter's state vector and covariance. They go to `strategy_state.parquet`, one row per track state row in the same order, as 32-bit floats. That file is large (about four times `track_state.parquet`). Like every run file it only exists where the run was made. A strategy that records state can offer a static `predict(state, seconds, params)`, see `strategy.py`; the viewer server calls it to look ahead.

Production is not stored as a run. The viewer converts the two tables when it opens a case (`production.py`) and finds the raw plots production used by matching position times: production copies a raw plot into a fused plot, so a raw plot was used when a fused plot from the same source has the same position time to the microsecond and the same aircraft: the same source track id for the append table, the same hex for the final table, which does not keep the source track id. Every other raw plot is `unknown`, because production never says why it left one out.

## Runs and versions

The label counts up per strategy and case, r001, r002, and so on. Nothing is overwritten, so an older version of a strategy stays available next to the new one. Each run folder holds a `run.json` that says what produced it:

- the strategy, the label, and the batch, one id shared by every run of one command, so the same code run on four cases can be found again as one group
- when it ran and how long it took
- the git commit of this repo at the time, and whether the working tree had uncommitted changes
- the strategy's parameters, from its `params` attribute
- the normalizer: its name, its parameters, and how many plots it kept and removed, per reason
- the note, and a few counts: raw plots, track updates, fused plots, tracks, plots later rewritten, raw plots per state and per reason
- the command line, so it can be pasted back

In the viewer, "all runs…" opens a table of every run of the case and the two production entries, sortable by any column; batch, commit and rewritten counts are only in the detail. Ticking "active" lists a run under Strategies on the left; when a case opens the newest run of every strategy but baseline is active, and production. A click on a row shows the full manifest, two ticked runs are compared field by field, and the note can be edited in place. The note is the only thing the viewer ever writes, into that run's `run.json`.

Runs are not committed. The whole `runs/` folder of every case is in `.gitignore`, because runs are large and anyone can make them again from the code. A fresh checkout has no runs, and the viewer then shows only the two production entries. To get the Kalman strategy, run it on every case from `src/` (about 25 minutes):

```bash
uv run -m harness.run --case data/cases --strategy kalman
```

## How a run works

`run.py` takes the raw plots in the order we received them, and each goes through three steps:

1. The normalizer (`normalization/basic.py`) turns the raw plot into a `Measurement`, or removes it, and says which in a `NormalizationResult`. The raw plot is the real source proto, for example `ADSBXPlot` or `AsterixCat021`, with the shared `Common` block inside. The Measurement has the same fields for every source, under plain names (`normalization/measurement.py`): the raw plot it came from, its times, position and altitude, whether it is on the ground, its kind, its accuracy as a 95% radius, its identity fields and its motion. All knowledge about the sources lives in the normalizer; a strategy never reads a raw plot.
2. The strategy answers the Measurement with a `StrategyResult`: `used`, `skipped` (refused on the measurement alone, without looking at a track) or `rejected` (compared with its track and refused), why, the track, numbers about this plot, and at most one `TrackUpdate`. Look at `strategy.py` for the interface and `strategies/baseline.py` for the smallest possible strategy.
3. At the end the output layer (`output.py`) writes the files.

The basic normalizer removes ADS-B Exchange MODE_S plots, an old position filled in next to a Mode S reply, and ADS-B Exchange type UNKNOWN. For the rest it sets:

- the kind: `own_gps` for the aircraft's own GPS position (ADS-B Exchange ADSB_ICAO, ADSB_ICAO_NT and ADSR_ICAO, uAvionix, PlaneFinder ADS-B), `mlat` for ADS-B Exchange MLAT, `radar` for TFMS Track Information and STDDS, `report` for TFMS oceanic reports, United and Alaska, and a plain label of its own for the rest (`tisb`, `adsc`, `adsb_other`, `planefinder_mlat`, `flarm`, ...)
- whether it is on the ground, for ADS-B Exchange (alt_baro "ground"), uAvionix and PlaneFinder; empty for sources that do not say
- the kind's time error, `time_sigma_s`, per source: uAvionix 0.05 s, ADS-B Exchange 0.15 s, PlaneFinder 0.6 s (whole seconds, stations that disagree); measured as the miss along the direction of flight divided by speed
- the track angle from the source's own field where the common block leaves it empty (ADS-B Exchange `track`, PlaneFinder `track_angle`)
- the hex as an identity, empty for values that cannot name one aircraft (000000, 000001, FFFFFF, too short)
- the accuracy as a 95% radius in metres: for own GPS with a NACp of 1 to 11 the NACp's radius; for own GPS without a usable NACp, whether it has none at all (most ADS-R, all PlaneFinder) or says 0 (every plot of an old version 0 transponder, whose positions are as good as others'), `own_gps_no_nacp_accuracy_95_m`, 36.75 m (15 m sigma); for MLAT `mlat_accuracy_95_m`, 1,102.5 m (450 m sigma; against a straight line over one minute MLAT plots stray a median 42 m and 95% under 400 m, a 150 m sigma, but their errors come in bursts of kilometres that neighbouring plots share, so the sigma is three times the measured one); empty for other kinds

A `TrackUpdate` says: from now on, this track between `since` and `until` consists of these points. An append is a span that is the new point's own time, with that one point; a rewrite of history is a span in the past with its new points. The harness gives each update the received time of the plot that caused it. A `TrackPoint` holds the fields of a fused plot and the strategy's numbers about the track at that point.

```python
return StrategyResult.used(TrackUpdate.append(track_id, point), distance_m=41.0)   # went into this track as a measurement
return StrategyResult.skipped("kind not used: radar")                             # refused on the measurement alone
return StrategyResult.rejected(track_id, "out of order")                          # compared with its track and refused
```

Keyword numbers become columns of the raw plot's row; a track point's `numbers` become columns of its track state row. The viewer colours and filters raw plots by the state, and offers every number in its charts. Point size by uncertainty uses `sigma_east_m`, `sigma_north_m` and `cov_east_north_m2` from `track_state` when a strategy gives them; without the covariance the ellipse's axes run east and north.

The baseline: one append per measurement, track id `<source>:<source track id>`, the measurement's fields copied into the point. No merging across sources, no filtering, no smoothing.

The Kalman strategy (`strategies/kalman.py`) keeps tracked objects: one aircraft each, ids `<hex>:<n>`, several per hex when the same hex is seen in places one aircraft cannot both be. It takes measurements of kind `own_gps` and `mlat` in the air, with a hex and an altitude, and skips the rest with the reason. Inside each object two constant velocity filters in ECEF run side by side on the same plots, a straight-flight one with a small process noise and a manoeuvre one with a large one, with weights that say how much each describes the aircraft right now; the object's position, velocity and uncertainty are their weighted mix (an interacting multiple model filter, see below). A plot is compared with every live object of its hex (an object without a plot for `die_after_s`, 300 s, is over): predicted forward to the plot's time when the plot is newer than the object's last plot, backward when it is older. Within `gate_sigmas` (5) of an object whose last plot is older, the plot is used by the object it fits best; objects that fit the same plot are one aircraft and the oldest goes on. Within the gate of where an object was, it is a late copy and rejected as "out of order". Otherwise, if the nearest object could have flown to it (`birth_speed_margin` 2 × speed × elapsed time, at least 1 s, over the ground) it is rejected as "far from the prediction", and after `restart_after_s` (30 s) of such refusals that object starts over at the plot, keeping its id. Only a plot no live object could have reached starts a new candidate object, which is published, with its history in one `TrackUpdate`, once plots have agreed with it for `confirm_after_s` (300 s); until then its plots are rejected as "candidate object". A new object starts moving as its first plot reports (ground speed, track angle, vertical rate, `reported_velocity_sigma_mps` 10 m/s per axis; `unknown_velocity_sigma_mps` 300 m/s when the plot reports no speed).

The measurement noise is the normalizer's 95% radius divided by 2.45 (a circle of 2.45 sigma holds 95% of positions spread evenly in east and north), made longer along the direction of flight by the speed times the source's `time_sigma_s`, because a plot whose time is off shows where the aircraft was that much earlier or later; the altitude gets its own `altitude_sigma_m` (10 m, barometric altitude in 25 ft steps, whatever the position accuracy). The process noise, how much the velocity may wander, is `spectral_density_straight` (1.0 (m/s²)² s, fits straight flight) for the straight model and `spectral_density_manoeuvre` (100, follows a standard-rate turn) for the manoeuvre model, east and north, and up `spectral_density_vertical` (0.5) for the straight model and `spectral_density_vertical_manoeuvre` (20) for the manoeuvre model, because a manoeuvre changes the vertical rate too. Before each prediction the two models are blended toward each other by the chance that the aircraft switched between flying straight and manoeuvring over the elapsed time, `1 - exp(-dt / switch_time_s)` with `switch_time_s` 120 s; after each used plot the weights move toward the model under whose prediction the plot was more likely. One process noise could not serve both: 1.0 lost every turn behind the gate, 10 followed most turns at a rough cruise and still lost 32 of them in the Dubai hour, 100 followed them all at a rougher cruise; two models give the turn losses of 100 with a cruise smoother than 10. Per plot it records `measurement_sigma_m`, `distance_m` and `distance_sigmas` (how far the plot was from where the object expected the aircraft), the same miss split `along_m` and `across_m` the direction of flight and `vertical_m`, and `horizontal_sigmas` and `vertical_sigmas`; `confirmed`, `restarted` and `merged` mark those events. Per track state it records `sigma_east_m`, `sigma_north_m`, `sigma_up_m`, `cov_east_north_m2`, `sigma_speed_mps` and `manoeuvre_weight`. Both models' states and covariances in ECEF go to `strategy_state.parquet` as `state_straight_x_m` … `state_manoeuvre_p_i_j` with the weights `state_weight_straight` and `state_weight_manoeuvre`, and `Kalman.predict` runs the same two-model step from there; it answers the mixed prediction and each model's own with the weight the prediction gives it at that time, which the viewer's look-ahead draws in the model's colour, fainter for less weight. Every rule and number came out of the experiment loop of September 2026 (`~/agent-office/tasks/kalman-experiment-loop/decisions.html`); `src/experiments/` is that loop's harness.

## Files

```
build_protos.py        compiles protos/ into generated/ (uv run src/harness/build_protos.py)
protos/                snapshot of the proto files, see protos/README.md for where they came from
generated/             the compiled Python modules, committed so nothing needs protoc to run
protos_path.py         puts generated/ on sys.path
raw_plots.py           raw/<source>.parquet rows -> source protos, sorted by receipt time
normalization/         measurement.py: the Measurement and NormalizationResult; basic.py: the normalizer
strategy.py            the interface every strategy follows: StrategyResult, TrackUpdate, TrackPoint
strategies/            baseline.py, kalman.py
runs.py                run folders, labels and the run.json manifest
run.py                 runs the normalizer and a strategy on one or more cases
output.py              writes a run's files to runs/<strategy>/<label>/
production.py          the two production tables as a strategy's output, for the viewer
protodocs.py           the comment next to every proto field, for the viewer's field list
field_notes.json       our own short description of every field, per source and for the strategy output
viewer/server.py       local server for a folder of cases
viewer/viewer.html     the page, with viewer.css and js/ (deck.gl map, uPlot charts, one module per part)
```

## The viewer

The map and the charts show what someone would have known at the timeline's now: raw plots we had received by then, and strategy plots that had been emitted and not yet replaced by a later rewrite. Nothing from the future is drawn. Space plays, arrow keys step one second, shift for ten.

The viewer never decides which plots are one aircraft. The only groupings it knows are a source's own track, one source and one track identifier, and a strategy's fused track. Comparing means picking some of those tracks and looking at them together.

**Left panel.** From the top: the case, time and comparing, raw plots, strategies, the NACp and NIC reference, and the controls. Inside raw plots and strategies each part is an indented block with its own heading.

**Time and comparing.** Plots fade to nothing over a window: 10 s up to 1 h, never, or a custom number of seconds. It starts at 5 min: a longer window keeps more plots on screen, and on the big cases that makes panning and zooming far out slow. While the compare list has tracks, the map shows everything, only the compared tracks, or everything but them. The first track put into an empty list switches this to only the compared tracks; a change after that stays.

**Raw plots.** A show switch, then three parts:

- *Colour*, one choice at a time with a legend under it: by source, by source and plot kind (ADS-B Exchange's type, PlaneFinder's data source; the eight largest get a colour, the rest share "other"), by source track id, by hex else tail else source track id, by the compare list (a compared track in its own colour, everything else grey, and everything grey while nothing is compared), or by what happened to the plot in an active strategy run (removed by the normalizer, used, skipped, rejected, unknown). The last one reads `raw_plots.parquet`.
- *Size*: fixed, with a slider, or by NACp or NIC, drawn as a filled circle of that radius in metres (the 95 % radius for NACp, the containment radius for NIC, from DO-260B), or by the sigma an active strategy run gave each plot it used (`measurement_sigma_m` in its `raw_plots.parquet`), drawn as the circle of 2.45 sigma that holds 95 %; a plot the run did not use has no sigma. A plot without the number gets a filled circle with a cross, and a plot that says 0, accuracy unknown, gets a hollow ring with a thick edge; both have the size in metres set by the slider in that mode (10 to 1,000 m, 100 m to start, on a gentle curve so small sizes take more of the slider's travel), so they grow and shrink with the zoom like the real circles. All of them are drawn as shapes, so they stay sharp at any size. Hovering finds the whole disc, the dark cross included, and where circles overlap the smallest one under the mouse wins.
- *Filters*, folded away under their heading until it is clicked open, with the count of filters on and plots failing them in the heading; each filter is folded and off until ticked: source and plot kind, altitude, NACp, NIC, lateness (received minus position time), ground speed, on the ground, hex, callsign, tail, and what a strategy run did with the plot, by state and reason. Ticking a filter, or clicking the empty part of its bar, switches it on and opens it, unticking (or clicking there again) folds it, and the arrow or the name folds a switched on filter, which then shows what it keeps in its header, for example "0 – 10,000 ft". A number filter keeps plots in a range (two thumbs, or type the ends), or plots that have it set, do not have it set, or have it 0. Two switches above the list say what happens: a plot that fails is hidden (the default) or shown grey, and a plot must pass every filter that is on or at least one; inside the source list ticked items mean either. The count of switched on filters and failing plots sits next to the heading.

**Strategies.** The active runs, each with a tick to draw it; the show box on the heading hides them all at once and keeps the ticks, and unticking a run leaves its tracks in the compare list. "all runs…" opens the table of every run. Then a points block and a lines block, each with its own show switch and its own colour: by run, by strategy, by track id, or by the compare list as for raw plots, with a legend. Points are solid with a thin black edge so they stand out from the line. Point size is fixed, with a slider in pixels, or the strategy's own uncertainty: an ellipse of 1, 2 or 2.45 sigma in metres (2.45 sigma holds 95% of the positions), from its recorded east and north sigmas and their covariance; points without a sigma then get the size in metres from the slider (50 m to start). Here too the smallest point under the mouse wins. In the uncertainty modes a switch "look ahead from the hovered point" asks the strategy's own `predict` where the aircraft is 5, 10, 20, 30 and 60 s after the hovered point and draws those ellipses dashed white with their times; while it is on, a strategy point under the mouse wins over raw plots. It needs `strategy_state.parquet`, so a run without it says so in the status line. The lines block has the width slider.

**Adding tracks to the comparison.** Click a raw plot for that source's track, click a strategy point for that strategy's track, click again to remove. If several tracks overlap under the cursor a list asks which one. Shift and drag with the left button draws a box that adds every track with a visible plot inside it; the right button draws a red box that removes them. The box at the top right adds every source track and drawn strategy track whose plots carry a hex, callsign or tail, and clear all empties the list. Every compared track has its own colour, shown on its chip and in the charts. The map uses those colours only where a colour menu on the left (raw plots, strategy points, strategy lines) is set to the compare list; adding a track does not change the menus. Show switches, sizes, widths and filters keep working. Each chip has an eye that hides that track from the map and the charts without removing it, and a × that removes it. The "comparing" switch next to clear all turns the list's effect on the map off and on: off, the map looks as if the list were empty, while the list and the charts stay.

**Charts** (right panel). Raw plot charts and strategy charts are kept apart, because their fields differ. "+ chart" opens the fields of that side: for raw plots every field of every source's proto that has numbers, plus the numbers a strategy recorded per raw plot; for strategies every fused plot field and every number recorded in `track_state`. Each field has an i: hovering it shows our own plain description of the field (written from the code and kept in `field_notes.json`), the comment next to the field in its proto (read from the proto snapshot by `protodocs.py`), what kind it is, how many rows carry it, its lowest and highest value, and for a greyed out field that no plot in this case carries it.

Fields come in three kinds, and each kind gets its own chart when several are picked. A number is charted as it is; when a mostly numeric field also holds words, like "ground" in ADS-B Exchange's alt_baro, the words get lanes of their own under the numbers. Text that reads as a date and time is charted as times of day and says "text as time" in the list and "Text read as times" on its chart. Other text, such as a callsign, squawk or hex (identifiers stay text even when they look like numbers), is charted in lanes: one lane per value, "not set" and "empty" included, in the order the values first appear in time, with a thin row inside every lane for each compared track. When the compared tracks carry more than 20 different values the chart draws nothing and says so. The numbers and text a strategy recorded per raw plot, including what it did with the plot (state, reason, the track it went into), are in the list under that run. Pick one or more fields, from several sources if you like, and the chart shows them against position time for the compared tracks: dots for source tracks, lines for strategy tracks, a second field of the same track hollow or dashed. Nothing is worked out from the fields; a chart shows what is stored. Click a legend item to hide or show a series, shift click to show only that one, shift click again for all. Drag the bar under a chart to change its height, × removes it. A switch above the charts picks what dragging inside a chart does. "A time window, all charts", the default, zooms the time axis: all charts follow, the map shows only that window, the timeline highlights it, and reset zoom or a double click brings the whole hour back. "A box, this chart only" zooms that chart to the rectangle you drag, in time and in value, and leaves the other charts, the map and the timeline alone; a double click resets that chart, and switching back to the time window drops every box. Hovering a point rings it on the map, just outside its own circle in its own units, and in every chart, with a card that names the plot, its times, its accuracy numbers, and what each active strategy run did with it. When several plots sit at exactly the same position, for example the same fix from ADS-B Exchange and uAvionix, each gets its own card in the same pop-up (up to 8, then a count).

**The address bar** holds only the case, so a link opens that case with every control at its default.

### The brand font

The viewer asks for Simplon ASI, the ASI brand typeface, in three families. Simplon ASI Norm carries the body text, Simplon ASI Mono the numbers and technical labels, and Simplon ASI Caps Mono and Caps Norm the headings. The font files are licensed to ASI for design and development, so they are not in this repository. `.gitignore` keeps `src/harness/viewer/fonts/` out.

Without them the page still works and still looks close to right. Each `font-family` in the stylesheet names Simplon ASI first and then an ordinary stack, so a browser that cannot find Simplon ASI falls through to Inter or the system sans for text, and to SF Mono, Menlo or Consolas for the mono. Every heading that relies on a caps face also carries `text-transform: uppercase`, so the capitals survive the fallback. The letter shapes and the line widths change a little. Nothing moves or breaks.

To get the real faces, download `Simplon_ASI.zip` from the Brand Identity 4.0 page in Notion, and copy the eight files from its `WOFF2` folders into `src/harness/viewer/fonts/`, keeping their names:

```
SimplonASINorm-Regular-Web.woff2      SimplonASINorm-Medium-Web.woff2
SimplonASIMono-Regular-Web.woff2      SimplonASIMono-Medium-Web.woff2
SimplonASICapsNorm-Regular-Web.woff2  SimplonASICapsNorm-Medium-Web.woff2
SimplonASICapsMono-Regular-Web.woff2  SimplonASICapsMono-Medium-Web.woff2
```

The viewer server serves that folder already, because it changes into the viewer directory and hands anything it does not recognise to the standard static file handler. Reload the page and the real faces appear.

## About the protos

The source schemas import the shared `Common` plot from `uni_track_plot_schema/proto/plot.proto`, a path that no checkout has any more because the file moved into uni-proto under a new package name. `protos/uni_track_plot_schema/proto/plot.proto` is a copy of the uni-proto version with the old package name, so the source schemas compile unchanged. The fields and numbers are identical, and a raw `Common` is copied into a `FusedPlot.common` by serialising and parsing, which works because the wire format is the same.

The case data itself is pulled with `src/data/cases/pull_case.py`: one Parquet file per source table in `raw/` and the two production fusion tables in `production/`, all columns. The bq JSON export rounds timestamps to whole seconds, so `src/data/cases/add_micros.py` recovers the exact microseconds from BigQuery's cached query results and stores them in `<column>_us` columns. The loader prefers those. Many cases at once go through `src/data/cases/pull_cases.py`: one query per source and day for all cases of that day, since a case costs a full day scan whatever its box, with the `_us` columns added in the query. The `fw01` to `fw30` cases were pulled that way from the visible error finder's Flyways list.

## Things noticed on the first case

- 1,259 of 172,337 raw plots arrived with an older position time than the previous plot of the same source track, so out of order input is real even within one source.
- uAvionix plots pulled before 22 September 2026 had two bugs from the integration: `common.altitude_ft` held the GPS height where every other source has the barometric altitude, and `common.ground_speed_kt` was in nautical miles per second instead of knots (the raw `airborne_ground_vector.ground_speed`, times 3600). Both are fixed in `uni-track-source-uavionix` (#113, #114). The case datasets, raw and the production tables, were corrected with `src/data/cases/fix_uavionix.py`, which records what it did in `case.json`. Cases pulled after the fix need nothing.
