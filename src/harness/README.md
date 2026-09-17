# Track harness

Replays real raw plots through a tracking strategy and shows the result next to what production did. This is the experiment pipeline of TS-1804: one case, all sources, the dumb baseline first, better strategies later.

Everything runs locally from Parquet files in `src/data/cases/<case>/`. Nothing here talks to a live system.

## Run it

```bash
# from the src folder
uv run -m harness.run --case data/cases/paris-tx-n464ae-2026-09-16 --strategy baseline
uv run -m harness.production --case data/cases/paris-tx-n464ae-2026-09-16
uv run -m harness.viewer.server --case data/cases/paris-tx-n464ae-2026-09-16
```

The first command feeds every raw plot of the case to the strategy and stores what it emitted under `runs/baseline/`. The second turns the two production fusion tables of the case into runs of the same shape, `prod_fusion_append` for what the append path first emitted and `prod_fusion_regular` for the result after the regular and recorrelation rewrites, so they can be compared like any strategy. The third opens the viewer at http://localhost:8770.

## How a strategy works

A strategy gets raw plots one at a time, in the order we received them, and answers with `FusionChangedEvent`s, the message uni-track-fusion publishes on Pulsar today. Look at `strategy.py` for the interface and `strategies/baseline.py` for the smallest possible one.

The raw plot is the real source proto, for example `ADSBXPlot` or `AsterixCat021`, with the shared `Common` block inside. The strategy can read every field the source sent, including the ADS-B quality numbers that production throws away.

An event names a track, says when it was produced, carries a quality flag (APPEND_ONLY, REGULAR or RECORRELATION), and holds one or more changed segments. A segment is a time span plus the fused plots that now make up that span. An append is a segment with the new plot at the end. A rewrite is a segment covering a span in the past. The viewer replays these, so at any moment it shows each track as consumers would have known it then.

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
run.py                 runs a strategy on a case, writes runs/<strategy>/events.bin and fused_plots.parquet
production.py          production tables -> runs/prod_fusion_append and runs/prod_fusion_regular
viewer/server.py       local server, viewer/viewer.html the page (deck.gl map, uPlot charts)
```

`events.bin` holds every event as length-prefixed protobuf bytes, exactly what a strategy emitted. `fused_plots.parquet` is the same flattened to one row per fused plot, with `created_at_us` (when the event was produced) and `valid_to_us` (when a later event on the same track replaced this plot, empty if never). The viewer shows a plot when `created_at <= now < valid_to`.

## The viewer

The map and the charts show what someone would have known at the timeline's now: raw plots we had received by then, and run plots that had been emitted and not yet replaced by a later rewrite. Nothing from the future is drawn. The timeline under the map is now in receipt time. Space plays, arrow keys step one second, shift for ten.

The viewer never decides which plots are one aircraft. The only groupings it knows are a source's own track, one source and one track identifier, and a run's fused track. Comparing means picking some of those tracks and looking at them together.

**Left panel.** Which raw sources and which runs to show. A run is drawn as lines per track, with rings on the plots as an option. Raw colour is by source, by lateness, or by a display key that is the hex, else the tail, else the source track id. That key is only a colour. Plots fade to nothing over a window you choose, default 15 minutes. "Grey out tracks not being compared" keeps the other traffic but colourless, and "map shows" switches between everything, only the compared tracks, and everything except them.

**Adding tracks to the comparison.** Click a raw plot for that source's track, click a fused plot for that run's track, click again to remove. If several tracks overlap under the cursor a list asks which one. Shift and drag with the left button draws a box that adds every track with a visible plot inside it; the right button draws a red box that removes them. The box at the top right adds every track whose plots carry a hex, callsign or tail, and clear all empties the list. Each compared track gets its own colour, as a thicker outline on the map and as a series in the charts. Click a chip to remove that track.

**Charts.** One series per compared track, dots for a source track and a line for a run track:

- altitude, ground speed, track angle
- lateness, received minus position time
- cross track distance: how far a raw plot sits sideways from the line through the neighbouring plots of another compared source track, so a 4 km disagreement between sources is one glance
- time since the previous plot of the same track, for coverage holes and bursts
- vertical rate worked out from consecutive altitudes per track
- which source each run track used, one row per source

Click a legend item to hide or show a series, shift click to show only that one, shift click again for all. Drag the bar under a chart to change its height, drag the panel's left edge to change its width. Drag inside a chart to zoom the time axis: all charts follow, the map shows only that window, the timeline highlights it, and reset zoom or a double click brings the whole hour back.

**Pins.** Shift click a plot on the map, or click a point in a chart, to pin it. Hovering a point anywhere rings it on the map and in every chart. Up to two pins, numbered on the map and the charts, with the differences between them listed above the charts: seconds apart in position time, metres apart, the speed that distance would need, feet and knots apart, and how far apart we received them. Click a pin's card to remove it, escape clears both.

## About the protos

The source schemas import the shared `Common` plot from `uni_track_plot_schema/proto/plot.proto`, a path that no checkout has any more because the file moved into uni-proto under a new package name. `protos/uni_track_plot_schema/proto/plot.proto` is a copy of the uni-proto version with the old package name, so the source schemas compile unchanged. The fields and numbers are identical, and a raw `Common` is copied into a `FusedPlot.common` by serialising and parsing, which works because the wire format is the same.

The case data itself is pulled with `src/data/cases/pull_case.py`, one Parquet file per source table plus the two production fusion tables, all columns. The bq JSON export rounds timestamps to whole seconds, so `src/data/cases/add_micros.py` recovers the exact microseconds from BigQuery's cached query results and stores them in `<column>_us` columns. The loader prefers those.

## Things noticed on the first case

- 1,259 of 172,337 raw plots arrived with an older position time than the previous plot of the same source track, so out of order input is real even within one source.
- uAvionix `common.ground_speed_kt` is not in knots. The median over the hour is 0.098 while ADS-B Exchange says 395 kt for the same traffic, and the value equals the raw `airborne_ground_vector.ground_speed`, which ASTERIX CAT021 defines in nautical miles per second. Multiply by 3600 to get knots. The wrong value reaches production: the 54 uAvionix rows in the final fused table have a median ground speed of 0.03 kt. Any strategy using uAvionix speed must convert, and the source adapter should be fixed.
