# Track harness

Replays real raw plots through a tracking strategy and shows the result next to what production did. In the viewer everything that produced fused plots is called a strategy, production included. This is the experiment pipeline of TS-1804: one case, all sources, the dumb baseline first, better strategies later.

Everything runs locally from Parquet files in `src/data/cases/<case>/`. Nothing here talks to a live system.

## Run it

```bash
# from the src folder
uv run -m harness.run --case data/cases/paris-tx-n464ae-2026-09-16 --strategy baseline --note "what this run tries"
uv run -m harness.viewer.server --cases data/cases
```

The first command feeds every raw plot of the case to the strategy and stores what it emitted under `runs/baseline/r001/`. The second opens the viewer at http://localhost:8770 with every case in the folder in a dropdown at the top. Production needs no command: the viewer reads the two production tables that came with the case and shows them as two more strategies, `prod_fusion_append` for what the append path first emitted and `prod_fusion_regular` for the result after the regular and recorrelation rewrites. `--port` picks another port and `--no-browser` keeps the server from opening a tab.

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
    raw_plots.parquet              what the strategy did with each raw plot
    track_state.parquet            what the strategy recorded about its tracks, when it recorded anything
    strategy_state.parquet         the strategy's own state per track row, for looking ahead
```

A raw plot is named by its source and its row number in `raw/<source>.parquet`.

`fused_plots.parquet` has one row per fused plot of every event the strategy returned: the event's number, track id, `created_at` and quality, the segment's `since` and `until`, every field of the fused plot under its proto name, and `valid_to`, the `created_at` of the first later event on the same track that covers this plot's position time, empty if none did. The viewer shows a plot when `created_at <= now < valid_to`, so a strategy that rewrites the past is replayed the way consumers would have seen it. Appends and rewrites sit in the same table; the quality column says which is which.

`raw_plots.parquet` has one row per raw plot: source, row, state, track id, reason, and one column per number the strategy recorded with that plot. `track_state.parquet` has one row per `record.track` call: track id, position time, and one column per number. The viewer matches a track state row to the fused plot of the same track and position time.

Numbers a strategy passes to `record.track` under a name starting with `state_` are its own state, for example the Kalman filter's state vector and covariance. They go to `strategy_state.parquet`, one row per track state row in the same order, as 32-bit floats. That file is large (about four times `track_state.parquet`). Like every run file it only exists where the run was made. A strategy that records state can offer a static `predict(state, seconds, params)`, see `strategy.py`; the viewer server calls it to look ahead.

Production is not stored as a run. The viewer converts the two tables when it opens a case (`production.py`) and finds the raw plots production used by matching position times: production copies a raw plot into a fused plot, so a raw plot was used when a fused plot from the same source has the same position time to the microsecond and the same aircraft: the same source track id for the append table, the same hex for the final table, which does not keep the source track id. Every other raw plot is `unknown`, because production never says why it left one out.

## Runs and versions

The label counts up per strategy and case, r001, r002, and so on. Nothing is overwritten, so an older version of a strategy stays available next to the new one. Each run folder holds a `run.json` that says what produced it:

- the strategy, the label, and the batch, one id shared by every run of one command, so the same code run on four cases can be found again as one group
- when it ran and how long it took
- the git commit of this repo at the time, and whether the working tree had uncommitted changes
- the strategy's parameters, read from a `params` attribute on the strategy if it has one
- the note, and a few counts: raw plots, events, fused plots, tracks, plots later rewritten, raw plots per state and per reason
- the command line, so it can be pasted back

In the viewer, "all runs…" opens a table of every run of the case and the two production entries, sortable by any column; batch, commit and rewritten counts are only in the detail. Ticking "active" lists a run under Strategies on the left; when a case opens the newest run of every strategy but baseline is active, and production. A click on a row shows the full manifest, two ticked runs are compared field by field, and the note can be edited in place. The note is the only thing the viewer ever writes, into that run's `run.json`.

Runs are not committed. The whole `runs/` folder of every case is in `.gitignore`, because runs are large and anyone can make them again from the code. A fresh checkout has no runs, and the viewer then shows only the two production entries. To get the Kalman strategy, run it on every case from `src/` (about 25 minutes):

```bash
uv run -m harness.run --case data/cases --strategy kalman
```

## How a strategy works

A strategy gets raw plots one at a time, in the order we received them, and answers each with a list of `FusionChangedEvent`s, the message uni-track-fusion publishes on Pulsar today. Next to the events it keeps a `Record`, handed to it once when the harness makes it, where it notes what it did with each raw plot and any numbers it wants to keep about its tracks. Look at `strategy.py` for the interface and `strategies/baseline.py` for the smallest possible one.

The raw plot is the real source proto, for example `ADSBXPlot` or `AsterixCat021`, with the shared `Common` block inside. The strategy can read every field the source sent, including the ADS-B quality numbers that production throws away.

An event names a track, says when it was produced, carries a quality flag (APPEND_ONLY, REGULAR or RECORRELATION), and holds one or more changed segments. A segment is a time span plus the fused plots that now make up that span. An append is a segment with the new plot at the end. A rewrite is a segment covering a span in the past.

The record takes one call per raw plot. The harness points it at the current plot before each `on_plot`, so the calls only say what happened:

```python
self.record.used(track.hex, distance_m=41.0)     # went into this track as a measurement
self.record.skipped("adsbx type not used: MODE_S")   # a fixed rule says this plot is not for this strategy
self.record.dropped("out of order", track.hex)   # the right kind of plot, but its timing made it unusable
self.record.rejected(track.hex, "too far")       # checked against a track and refused
self.record.track(track.hex, sigma_east_m=12.3)  # numbers about the track as of this plot's position time
```

Extra keyword numbers become columns: on the raw plot's row for the first four, on the track's row for `track`. A plot the strategy says nothing about is stored as `unknown`, and two outcome calls for one plot stop the run with an error. The viewer colours and filters raw plots by the state, and offers every recorded number in its charts. Point size by uncertainty uses `sigma_east_m`, `sigma_north_m` and `cov_east_north_m2` from `track_state` when a strategy records them; without the covariance the ellipse's axes run east and north.

The baseline: one event per raw plot, quality APPEND_ONLY, track id `<source>:<source track id>`, one segment with the raw common block copied into a fused plot. No merging across sources, no filtering, no smoothing.

The Kalman strategy (`strategies/kalman.py`): a constant velocity filter per hex on plots in the air. It uses the aircraft's own GPS position from ADS-B Exchange (types ADSB_ICAO, ADSB_ICAO_NT, ADSR_ICAO, ADSB_OTHER and ADSR_OTHER; the last two have no ICAO address and are keyed by ADS-B Exchange's own `~` address), uAvionix and PlaneFinder ADS-B, plus ADS-B Exchange MLAT. The measurement noise is half the NACp 95% radius; an own GPS plot without NACp (most ADS-R, all PlaneFinder) gets `own_gps_no_nacp_sigma_m`, NACp 0 gets `default_sigma_m`, and MLAT gets `mlat_sigma_m`. A PlaneFinder plot at exactly the position of a plot the filter used for that aircraft in the last 10 s is dropped as a copy of that fix. There is no outlier check and no model of time errors yet. It records, per used plot, `distance_m` and `distance_sigmas`: how far the plot was from where the filter expected the aircraft, in metres and in sigmas, and `measurement_sigma_m`, the noise it gave the plot. Per track state it records `sigma_east_m`, `sigma_north_m`, `sigma_up_m`, `cov_east_north_m2` (the east-north covariance, for the uncertainty ellipse) and `sigma_speed_mps`. Its state vector and covariance in ECEF go to `strategy_state.parquet` as `state_x_m` … `state_vz_mps` and `state_p_i_j`, and `Kalman.predict` runs its own constant velocity step and process noise from there. Its measurement and process noise are the same east and north, so today its ellipse is a circle and the covariance 0 up to rounding (correlation at most 0.0001).

## Files

```
build_protos.py        compiles protos/ into generated/ (uv run src/harness/build_protos.py)
protos/                snapshot of the proto files, see protos/README.md for where they came from
generated/             the compiled Python modules, committed so nothing needs protoc to run
protos_path.py         puts generated/ on sys.path
raw_plots.py           raw/<source>.parquet rows -> source protos, sorted by receipt time
strategy.py            the interface every strategy follows, and the Record
strategies/            baseline.py, kalman.py
runs.py                run folders, labels and the run.json manifest
run.py                 runs a strategy on one or more cases, writes runs/<strategy>/<label>/
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

**Time and comparing.** Plots fade to nothing over a window: 10 s up to 1 h, never, or a custom number of seconds. It starts at 5 min: a longer window keeps more plots on screen, and on the big cases that makes panning and zooming far out slow. While the compare list has tracks, the map shows everything, only the compared tracks, or everything but them.

**Raw plots.** A show switch, then three parts:

- *Colour*, one choice at a time with a legend under it: by source, by source and plot kind (ADS-B Exchange's type, PlaneFinder's data source; the eight largest get a colour, the rest share "other"), by source track id, by hex else tail else source track id, or by what an active strategy run did with the plot (used, skipped, dropped, rejected, unknown). The last one reads `raw_plots.parquet`.
- *Size*: fixed, with a slider, or by NACp or NIC, drawn as a filled circle of that radius in metres (the 95 % radius for NACp, the containment radius for NIC, from DO-260B). A plot without the number gets a filled circle with a cross, and a plot that says 0, accuracy unknown, gets a hollow ring with a thick edge; both have the size in metres set by the slider in that mode (10 to 1,000 m, 100 m to start, on a gentle curve so small sizes take more of the slider's travel), so they grow and shrink with the zoom like the real circles. All of them are drawn as shapes, so they stay sharp at any size. Hovering finds the whole disc, the dark cross included, and where circles overlap the smallest one under the mouse wins.
- *Filters*, each folded and off until ticked: source and plot kind, altitude, NACp, NIC, lateness (received minus position time), ground speed, on the ground, hex, callsign, tail, and what a strategy run did with the plot, by state and reason. Ticking a filter, or clicking the empty part of its bar, switches it on and opens it, unticking (or clicking there again) folds it, and the arrow or the name folds a switched on filter, which then shows what it keeps in its header, for example "0 – 10,000 ft". A number filter keeps plots in a range (two thumbs, or type the ends), or plots that have it set, do not have it set, or have it 0. Two switches above the list say what happens: a plot that fails is hidden (the default) or shown grey, and a plot must pass every filter that is on or at least one; inside the source list ticked items mean either. The count of switched on filters and failing plots sits next to the heading.

**Strategies.** The active runs, each with a tick to draw it; the show box on the heading hides them all at once and keeps the ticks, and unticking a run leaves its tracks in the compare list. "all runs…" opens the table of every run. Then a points block and a lines block, each with its own show switch and its own colour: by run, by strategy, or by track id, with a legend. Points are solid with a thin black edge so they stand out from the line. Point size is fixed, with a slider in pixels, or the strategy's own uncertainty: an ellipse of 1, 2 or 2.45 sigma in metres (2.45 sigma holds 95% of the positions), from its recorded east and north sigmas and their covariance; points without a sigma then get the size in metres from the slider (50 m to start). Here too the smallest point under the mouse wins. In the uncertainty modes a switch "look ahead from the hovered point" asks the strategy's own `predict` where the aircraft is 5, 10, 20, 30 and 60 s after the hovered point and draws those ellipses dashed white with their times; while it is on, a strategy point under the mouse wins over raw plots. It needs `strategy_state.parquet`, so a run without it says so in the status line. The lines block has the width slider.

**Adding tracks to the comparison.** Click a raw plot for that source's track, click a strategy point for that strategy's track, click again to remove. If several tracks overlap under the cursor a list asks which one. Shift and drag with the left button draws a box that adds every track with a visible plot inside it; the right button draws a red box that removes them. The box at the top right adds every source track and drawn strategy track whose plots carry a hex, callsign or tail, and clear all empties the list. While the list has tracks, every compared track has its own colour, source tracks by source track id and strategy tracks by their own track id, everything else turns grey, and only the colour menus on the left are dimmed until the list is empty again; show switches, sizes, widths and filters keep working. Each chip has an eye that hides that track from the map and the charts without removing it, and a × that removes it. The "comparing" switch next to clear all turns the list's effect on the map off and on: off, the map looks as if the list were empty, while the list and the charts stay.

**Charts** (right panel). Raw plot charts and strategy charts are kept apart, because their fields differ. "+ chart" opens the fields of that side: for raw plots every field of every source's proto that has numbers, plus the numbers a strategy recorded per raw plot; for strategies every fused plot field and every number recorded in `track_state`. Each field has an i: hovering it shows our own plain description of the field (written from the code and kept in `field_notes.json`), the comment next to the field in its proto (read from the proto snapshot by `protodocs.py`), what kind it is, how many rows carry it, its lowest and highest value, and for a greyed out field that no plot in this case carries it.

Fields come in three kinds, and each kind gets its own chart when several are picked. A number is charted as it is; when a mostly numeric field also holds words, like "ground" in ADS-B Exchange's alt_baro, the words get lanes of their own under the numbers. Text that reads as a date and time is charted as times of day and says "text as time" in the list and "Text read as times" on its chart. Other text, such as a callsign, squawk or hex (identifiers stay text even when they look like numbers), is charted in lanes: one lane per value, "not set" and "empty" included, in the order the values first appear in time, with a thin row inside every lane for each compared track. When the compared tracks carry more than 20 different values the chart draws nothing and says so. The numbers and text a strategy recorded per raw plot, including what it did with the plot (state, reason, the track it went into), are in the list under that run. Pick one or more fields, from several sources if you like, and the chart shows them against position time for the compared tracks: dots for source tracks, lines for strategy tracks, a second field of the same track hollow or dashed. Nothing is worked out from the fields; a chart shows what is stored. Click a legend item to hide or show a series, shift click to show only that one, shift click again for all. Drag the bar under a chart to change its height, × removes it. A switch above the charts picks what dragging inside a chart does. "A time window, all charts", the default, zooms the time axis: all charts follow, the map shows only that window, the timeline highlights it, and reset zoom or a double click brings the whole hour back. "A box, this chart only" zooms that chart to the rectangle you drag, in time and in value, and leaves the other charts, the map and the timeline alone; a double click resets that chart, and switching back to the time window drops every box. Hovering a point rings it on the map, just outside its own circle in its own units, and in every chart, with a card that names the plot, its times, its accuracy numbers, and what each active strategy run did with it.

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
