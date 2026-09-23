# Track harness

Replays real raw plots through a tracking strategy and shows the result next to what production did. In the viewer everything that produced fused plots is called a strategy, production included. This is the experiment pipeline of TS-1804: one case, all sources, the dumb baseline first, better strategies later.

Everything runs locally from Parquet files in `src/data/cases/<case>/`. Nothing here talks to a live system.

## Run it

```bash
# from the src folder
uv run -m harness.run --case data/cases/paris-tx-n464ae-2026-09-16 --strategy baseline --note "what this run tries"
uv run -m harness.production --case data/cases/paris-tx-n464ae-2026-09-16
uv run -m harness.viewer.server --cases data/cases
```

The first command feeds every raw plot of the case to the strategy and stores what it emitted under `runs/baseline_append/r001/`. The second turns the two production fusion tables of the case into the same output shape, `prod_fusion_append` for what the append path first emitted and `prod_fusion_regular` for the result after the regular and recorrelation rewrites, so production shows up in the viewer as two more strategies. The third opens the viewer at http://localhost:8770 with every case in the folder in a dropdown at the top; a case without strategy output is listed but greyed until the first two commands have run for it.

`--case` also takes a folder of cases, so `--case data/cases` runs the strategy on every case in one go. `--note` is free text kept with the run.

## Runs and versions

A strategy's output is stored the way production stores its own: the plots it appended in `runs/<strategy>_append/<label>/`, and the rewrites it made later in `runs/<strategy>_regular/<label>/`, like `prod_fusion_append` and `prod_fusion_regular`. A part without events gets no folder, and rewrites are not supported yet: a strategy that emits a REGULAR or RECORRELATION event stops the run with an error. The label counts up per strategy and case, r001, r002, and so on, and one execution gives both parts the same label. Nothing is overwritten, so an older version of a strategy stays available next to the new one. Each run folder holds a `run.json` that says what produced it:

- the strategy, the label, and the batch, one id shared by every run of one command, so the same code run on four cases can be found again as one group
- when it ran and how long it took
- the git commit of this repo at the time, and whether the working tree had uncommitted changes
- the strategy's parameters, read from a `params` attribute on the strategy if it has one
- the note, and a few counts: raw plots, events, fused plots, tracks, plots later rewritten, raw plots per outcome state and per skip reason
- the command line, so it can be pasted back

The viewer's toolbar shows the newest run of every strategy. The "more…" button on the strategies group opens a table of every run of the case, sortable by any column, where any run can be switched on, the note can be edited in place, a click shows the full manifest, and two ticked runs are compared field by field. The note is the only thing the viewer ever writes, into that run's `run.json`.

Every run is committed, strategy runs and production runs alike, so a version in the runs panel can be opened on any checkout.

## How a strategy works

A strategy gets raw plots one at a time, in the order we received them, and answers each with a `Result`: the `FusionChangedEvent`s it emits, the message uni-track-fusion publishes on Pulsar today, and the `Outcome` of that plot. Look at `strategy.py` for the interface and `strategies/baseline.py` for the smallest possible one.

The raw plot is the real source proto, for example `ADSBXPlot` or `AsterixCat021`, with the shared `Common` block inside. The strategy can read every field the source sent, including the ADS-B quality numbers that production throws away.

An event names a track, says when it was produced, carries a quality flag (APPEND_ONLY, REGULAR or RECORRELATION), and holds one or more changed segments. A segment is a time span plus the fused plots that now make up that span. An append is a segment with the new plot at the end. A rewrite is a segment covering a span in the past. The viewer replays these, so at any moment it shows each track as consumers would have known it then.

An outcome is a state and a few words of reason. `used` means the plot went into a track as a measurement, and the outcome names the track. `skipped` means a fixed rule says this kind of plot is not for this strategy, with the rule as the reason, for example "type 7" or "no altitude". `dropped` means the right kind of plot whose timing made it unusable, "out of order" or "duplicate". `rejected` means the plot was checked against a track and refused, for a strategy with a distance check. Production runs only know `used`, found by matching position times, and `unknown` for the rest. The harness stores the outcomes in `raw_outcomes.parquet` and counts them per state and per reason in `run.json`; the viewer colours and filters raw plots by them.

The baseline: one event per raw plot, quality APPEND_ONLY, track id `<source>:<source track id>`, one segment with the raw common block copied into a fused plot. No merging across sources, no filtering, no smoothing.

## Files

```
build_protos.py        compiles protos/ into generated/ (uv run src/harness/build_protos.py)
protos/                snapshot of the proto files, see protos/README.md for where they came from
generated/             the compiled Python modules, committed so nothing needs protoc to run
protos_path.py         puts generated/ on sys.path
raw_plots.py           Parquet rows -> source protos, sorted by receipt time
strategy.py            the interface every strategy follows
strategies/baseline.py the dumb baseline
runs.py                run folders, labels and the run.json manifest
run.py                 runs a strategy on one or more cases, writes runs/<strategy>_append/<label>/
production.py          production tables -> runs/prod_fusion_append/<label> and runs/prod_fusion_regular/<label>
viewer/server.py       local server for a folder of cases, viewer/viewer.html the page (deck.gl map, uPlot charts)
```

In a run folder, `events.bin` holds every event as length-prefixed protobuf bytes, exactly what a strategy emitted. `fused_plots.parquet` is the same flattened to one row per fused plot, with `created_at_us` (when the event was produced) and `valid_to_us` (when a later event on the same track replaced this plot, empty if never). The viewer shows a plot when `created_at <= now < valid_to`. `raw_outcomes.parquet` has one row per raw plot with its state, the track it went into and the reason.

## The viewer

The map and the charts show what someone would have known at the timeline's now: raw plots we had received by then, and strategy plots that had been emitted and not yet replaced by a later rewrite. Nothing from the future is drawn. The timeline under the map is now in receipt time. Space plays, arrow keys step one second, shift for ten.

The viewer never decides which plots are one aircraft. The only groupings it knows are a source's own track, one source and one track identifier, and a strategy's fused track. Comparing means picking some of those tracks and looking at them together.

**Toolbar over the map.** Which raw sources and which strategies to show, and whether a strategy is drawn as lines per track, rings on the plots, or both. The strategies group lists the newest run of each strategy; "more…" opens the table of all runs (see Runs and versions).

**Left panel.** The case, then display: raw plot colour is by source, by lateness, or by a display key that is the hex, else the tail, else the source track id. That key is only a colour. Strategy colour is by strategy, or by fused track id so every track gets its own colour. Raw plot size is fixed, or the NACp accuracy radius, or the NIC containment radius, drawn as circles in metres so the accuracy of a plot is visible as an area; plots without the chosen number stay as light grey dots of the normal size in those modes, and plots that carry it as 0, meaning the aircraft calls its accuracy unknown, are bright white. "Only plots that carry NIC or NACp" hides the sources without accuracy numbers, PlaneFinder and TFMS. A collapsible reference under the display options holds the DO-260B tables for NACp and NIC and a short explanation of NACv, SIL, NICbaro, GVA and SDA. Plots fade to nothing over a window you choose, default 15 minutes. "Grey out tracks not being compared" keeps the other traffic but colourless, and "map shows" switches between everything, only the compared tracks, and everything except them. Under those, the keyboard and mouse controls sit in a collapsible list, open on a first visit and closed again on every later one once you close it.

**Raw plot filters.** A collapsible section in the left panel narrows the raw plots to the ones a strategy can use, or to any other slice: the kind of plot inside a source (ADS-B Exchange's type, PlaneFinder's data source), NACp present or at least a value, an altitude present, not on the ground, a hex present, a lateness limit, and the outcome a chosen strategy run gave the plot, by state and by reason. Plots that fail a filter turn a dark grey, or disappear with the "hide" switch; the debug box counts them. The raw plot colour menu also offers "outcome for <strategy run>", one colour per state.

**Adding tracks to the comparison.** Click a raw plot for that source's track, click a fused plot for that strategy's track, click again to remove. If several tracks overlap under the cursor a list asks which one. Shift and drag with the left button draws a box that adds every track with a visible plot inside it; the right button draws a red box that removes them. The box at the top right adds every source track and strategy track whose plots carry a hex, callsign or tail, and clear all empties the list. Each compared track gets its own colour, as a thicker outline on the map and as a series in the charts. Click a chip to remove that track.

Under the chips a table gives a few numbers per compared track: plots, how many were later rewritten and how long after (median and worst, strategy tracks only), the largest jump between consecutive plots as an implied speed, the largest altitude step, lateness p50 and p99 (received minus position time for a source track, emitted minus position time for a strategy track).

**Charts.** One series per compared track, dots for a source track and a line for a strategy track:

- altitude as the shared `altitude_ft` field, then barometric altitude and geometric height from each source's own fields (raw plots only), ground speed, track angle
- lateness, received minus position time
- cross track distance: how far a raw plot sits sideways from the line through the neighbouring plots of another compared source track, so a 4 km disagreement between sources is one glance
- time since the previous plot of the same track, for coverage holes and bursts
- vertical rate worked out from consecutive altitudes per track

Click a legend item to hide or show a series, shift click to show only that one, shift click again for all. Drag the bar under a chart to change its height, drag the panel's left edge to change its width. Drag inside a chart to zoom the time axis: all charts follow, the map shows only that window, the timeline highlights it, and reset zoom or a double click brings the whole hour back.

**The address bar** carries the whole view: case, compared tracks, timeline position, zoom window, map position and every toggle. It updates as you work, so copying it at any moment gives a link that opens the same view.

**Pins.** Shift click a plot on the map, or click a point in a chart, to pin it. Hovering a point anywhere rings it on the map and in every chart, and the card on the map names the kind of plot inside the source where a source has more than one: ADS-B, MLAT, ADS-R or TIS-B for ADS-B Exchange, ADS-B, PlaneFinder MLAT or third party MLAT for PlaneFinder. Up to two pins, numbered on the map and the charts, with the differences between them listed above the charts: seconds apart in position time, metres apart, the speed that distance would need, feet and knots apart, and how far apart we received them. Click a pin's card to remove it, escape clears both.

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

The case data itself is pulled with `src/data/cases/pull_case.py`, one Parquet file per source table plus the two production fusion tables, all columns. The bq JSON export rounds timestamps to whole seconds, so `src/data/cases/add_micros.py` recovers the exact microseconds from BigQuery's cached query results and stores them in `<column>_us` columns. The loader prefers those. Many cases at once go through `src/data/cases/pull_cases.py`: one query per source and day for all cases of that day, since a case costs a full day scan whatever its box, with the `_us` columns added in the query. The `fw01` to `fw30` cases were pulled that way from the visible error finder's Flyways list.

## Things noticed on the first case

- 1,259 of 172,337 raw plots arrived with an older position time than the previous plot of the same source track, so out of order input is real even within one source.
- uAvionix plots pulled before 22 September 2026 had two bugs from the integration: `common.altitude_ft` held the GPS height where every other source has the barometric altitude, and `common.ground_speed_kt` was in nautical miles per second instead of knots (the raw `airborne_ground_vector.ground_speed`, times 3600). Both are fixed in `uni-track-source-uavionix` (#113, #114). The case datasets, raw and the production tables, were corrected with `src/data/cases/fix_uavionix.py`, which records what it did in `case.json`. Cases pulled after the fix need nothing.
