"""Local viewer: raw plots underneath, strategy output replayed on top, one case at a time.

usage: uv run -m harness.viewer.server [--cases data/cases] [--port 8770]

Every folder under --cases with a case.json is a case. The page gets a few base columns of every raw plot and
every strategy's fused plots up front, and any other field only when a chart asks for it.
"""
from __future__ import annotations

import argparse, json, os, pathlib, threading, webbrowser
from concurrent.futures import Future, ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .. import production, protodocs
from .. import runs as runbook
from ..raw_plots import SOURCE_MESSAGE
from ..run import STRATEGIES
from ..strategy import STATE_PREFIX

HERE = pathlib.Path(__file__).parent
# our own plain description of every field, per source and for the strategy output ("fused"), written from the code
NOTES_PATH = HERE.parent / "field_notes.json"
NOTES = json.loads(NOTES_PATH.read_text()) if NOTES_PATH.exists() else {}
RAW_SOURCES = ["adsbx", "planefinder", "uavionix", "stdds", "tfms_ti", "tfms_or", "ual", "asa"]
ADSBX_KIND = {1: "ADS-B", 2: "ADS-B, no position in message", 3: "ADS-R", 4: "TIS-B", 5: "TIS-B track file", 6: "ADS-C", 7: "MLAT", 8: "Mode S only", 9: "ADS-B other", 10: "ADS-R other", 11: "TIS-B other", 12: "other"}
PLANEFINDER_KIND = {1: "ADS-B", 2: "PlaneFinder MLAT", 3: "FLARM", 4: "third party MLAT", 5: "blocked"}
# ADS-B accuracy numbers where the source carries them
NACP_COLUMN = {"adsbx": "nac_p", "uavionix": "quality_indicators.nacp", "stdds": "status.nacp"}
NIC_COLUMN = {"adsbx": "nic", "uavionix": "quality_indicators.nucp_or_nic", "stdds": "status.nic"}


# ---------- small helpers ----------

def jsonable(series: pd.Series) -> list:
    """One array per column for the page: numbers as numbers, nulls as None, text as text."""
    if pd.api.types.is_bool_dtype(series) or pd.api.types.is_numeric_dtype(series):
        values = series.to_numpy(dtype=float, na_value=np.nan).tolist()
        return [None if v != v else (int(v) if v.is_integer() else round(v, 6)) for v in values]
    return series.fillna("").astype(str).tolist()


def number(frame: pd.DataFrame, column: str | None) -> pd.Series:
    """A numeric column, or all missing when the table has no such column."""
    if column is None or column not in frame.columns:
        return pd.Series([None] * len(frame), index=frame.index, dtype="Float64")
    return pd.to_numeric(frame[column], errors="coerce")


def text(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].fillna("").astype(str) if column in frame.columns else pd.Series([""] * len(frame), index=frame.index)


def micros(frame: pd.DataFrame, column: str) -> pd.Series:
    """A timestamp in microseconds: the exact twin column (<column>_us) when the pull recovered one."""
    twin = column.replace(".", "_") + "_us"
    return number(frame, twin if twin in frame.columns else column)


# codes and names stay text even when they look like numbers: a squawk is a code, not a quantity, and loses leading zeros as a number
IDENTIFIERS = ("squawk", "hex", "callsign", "flight", "tail_number", "tail", "registration", "track_identifier", "icao24", "flight_id", "flight_number", "flight_ref")


def classify(series: pd.Series) -> tuple[str, pd.Series, pd.Series | None]:
    """A column as chart values, and what kind they are:
    number   numbers, true/false as 1/0; words mixed in (like "ground" for an altitude) come back separately
    time     text that reads as a date and time, as microseconds since 1970
    text     anything else, missing kept apart from empty"""
    present = series.dropna()
    if present.empty:
        return "number", pd.Series([None] * len(series), index=series.index, dtype="Float64"), None
    if str(series.name).split(".")[-1] in IDENTIFIERS:
        return "text", series.where(series.isna(), series.astype(str)), None
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        return "number", series, None   # stored as numbers: nothing to judge
    text = present.astype(str)
    if text.str.lower().isin(["true", "false"]).all():
        return "number", series.astype(str).str.lower().map({"true": 1, "false": 0}).where(series.notna()), None
    numbers = pd.to_numeric(series, errors="coerce")
    filled = text[text != ""]
    if numbers.notna().sum() >= 0.9 * max(len(filled), 1):
        words = series.where(numbers.isna() & series.notna() & (series.astype(str) != ""))
        return "number", numbers, words if words.notna().any() else None
    if not pd.api.types.is_numeric_dtype(series):
        times = pd.to_datetime(series, utc=True, errors="coerce", format="mixed")
        if times.notna().sum() >= 0.9 * max(len(filled), 1):
            micros = (times - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(microseconds=1)
            return "time", pd.Series(micros, index=series.index).where(times.notna()), None
    return "text", series.where(series.isna(), series.astype(str)), None


def as_values(series: pd.Series) -> pd.Series:
    return classify(series)[1]


def jsonable_text(series: pd.Series) -> list:
    """Text for the page with missing kept as None, so "not set" and "empty" stay apart."""
    return [None if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v) for v in series.tolist()]


def field_payload(kind: str, values: pd.Series, words: pd.Series | None) -> dict:
    return dict(kind=kind, values=jsonable_text(values) if kind == "text" else jsonable(pd.to_numeric(values, errors="coerce")),
                words=jsonable_text(words) if words is not None else None)


def schema(frame: pd.DataFrame, skip: set[str], docs: dict[str, str] | None = None, notes: dict[str, str] | None = None) -> list[dict]:
    """The fields of a table: name, kind (number or text), on how many rows it is set, the lowest and highest value
    of a number, and the comment next to the field in its proto when there is one."""
    out = []
    for column in frame.columns:
        if column in skip or column.endswith("_us") or column.startswith("_"):
            continue
        present = frame[column].dropna()
        if len(present) and not np.isscalar(present.iloc[0]):
            continue   # repeated fields are not chartable
        kind, values, words = classify(frame[column])
        filled = values.notna() & (values.astype(str) != "") if kind == "text" else values.notna()
        field = dict(name=column, kind=kind, count=int(filled.sum()), doc=(docs or {}).get(column, ""), note=(notes or {}).get(column, ""))
        if kind in ("number", "time") and field["count"]:
            field.update(min=jsonable(pd.Series([values.min()]))[0], max=jsonable(pd.Series([values.max()]))[0])
        if kind == "text":
            field["distinct"] = int(values[filled].nunique())
        if words is not None:
            field["words"] = sorted(words.dropna().astype(str).unique().tolist())[:20]
        out.append(field)
    return out


# ---------- a case, loaded once ----------

class Case:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.info = json.loads((path / "case.json").read_text())
        self.t0_us = int(pd.Timestamp(self.info["t_start"], tz="UTC").timestamp() * 1e6)
        self.t1_us = int(pd.Timestamp(self.info["t_end"], tz="UTC").timestamp() * 1e6)
        self.sources: dict[str, pd.DataFrame] = {}
        self.raw_order: pd.DataFrame | None = None   # source and row of every raw plot, in the page's order
        self.raw_payload: dict | None = None
        self.schema_job: Future | None = None   # the sources' fields for the field list, built in the background
        self.runs: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]] = {}   # id -> fused, raw outcomes, track state

    def ms(self, us: pd.Series) -> pd.Series:
        """Microseconds since the epoch to milliseconds after the case start, the page's time axis."""
        return (us - self.t0_us) // 1000

    def run_list(self) -> list[dict]:
        """Every strategy run with its manifest, then the two production entries."""
        out = runbook.list_runs(self.path)
        for r in out:
            r["predicts"] = hasattr(STRATEGIES.get(r.get("strategy")), "predict")   # the viewer can look ahead from its fused plots
        for name, part in production.PARTS.items():
            path = self.path / "production" / f"{part}.parquet"
            if path.exists():
                # one fused plot per row, counted from the file's footer so the list can show it before the run is loaded
                out.append(dict(id=name, strategy=name, label="", production=True, counts=dict(fused_plots=pq.ParquetFile(path).metadata.num_rows),
                                note=f"production, from the case's production/{part}.parquet"))
        return out

    # the raw plots

    def source(self, name: str) -> pd.DataFrame:
        if name not in self.sources:
            path = self.path / "raw" / f"{name}.parquet"
            self.sources[name] = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        return self.sources[name]

    def raw(self) -> dict:
        """The base columns of every raw plot, sorted by the time we received them, and every source's fields."""
        if self.raw_payload is not None:
            return self.raw_payload
        parts = []
        for name in RAW_SOURCES:
            f = self.source(name)
            if f.empty:
                continue
            parts.append(pd.DataFrame(dict(
                src=name, row=range(len(f)),
                t=self.ms(micros(f, "common.position_timestamp")), r=self.ms(micros(f, "common.asi_received_timestamp")),
                lat=number(f, "common.latitude"), lon=number(f, "common.longitude"),
                alt=number(f, "common.altitude_ft"), gs=number(f, "common.ground_speed_kt"), trk=number(f, "common.track_deg"),
                cs=text(f, "common.callsign"), hex=text(f, "common.adshex"), tail=text(f, "common.tail_number"), tid=text(f, "common.track_identifier"),
                nacp=number(f, NACP_COLUMN.get(name)), nic=number(f, NIC_COLUMN.get(name)), rc=number(f, "rc" if name == "adsbx" else None),
                kind=plot_kind(f, name), ground=on_ground(f, name),
            )))
        frame = pd.concat(parts, ignore_index=True).sort_values("r", kind="stable").reset_index(drop=True)
        self.raw_order = frame[["src", "row"]]
        self.raw_payload = {c: jsonable(frame[c]) for c in frame.columns}
        # judging every column for the field list takes seconds on a big case: start it now, next to everything else
        self.schema_job = ThreadPoolExecutor(max_workers=1, thread_name_prefix="schema").submit(self.raw_schema)
        return self.raw_payload

    def raw_schema(self) -> dict:
        """Every source's fields for the field list. It only reads the source tables, which raw() has loaded."""
        return {name: schema(self.source(name), set(), protodocs.flat(SOURCE_MESSAGE[name].DESCRIPTOR.full_name), NOTES.get(name)) for name in RAW_SOURCES if not self.source(name).empty}

    def raw_field(self, source: str, column: str) -> dict | None:
        """One field of one source, lined up with the page's raw plots; plots of other sources get None."""
        if column not in self.source(source).columns:
            return None
        kind, values, words = classify(self.source(source)[column])
        rows, picks = self.raw_order["src"] == source, self.raw_order.loc[self.raw_order["src"] == source, "row"].to_numpy()
        def on_page(series: pd.Series | None) -> pd.Series | None:
            if series is None:
                return None
            page = pd.Series([None] * len(self.raw_order), dtype="object")
            page[rows] = series.iloc[picks].to_numpy()
            return page
        return field_payload(kind, on_page(values), on_page(words))

    # the strategies

    def load_run(self, run_id: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
        if run_id not in self.runs:
            if run_id in production.PARTS:
                fused, outcomes = production.load(self.path, run_id)
                state = None
            else:
                folder = self.path / "runs" / run_id
                fused, outcomes = pd.read_parquet(folder / "fused_plots.parquet"), pd.read_parquet(folder / "raw_plots.parquet")
                state = pd.read_parquet(folder / "track_state.parquet") if (folder / "track_state.parquet").exists() else None
                # the strategy's own state, for predict(); only where the run was made locally, it is not committed
                # its rows are the track_state rows in the same order, so the two sit side by side
                if state is not None and (folder / "strategy_state.parquet").exists():
                    own = pd.read_parquet(folder / "strategy_state.parquet")
                    if len(own) == len(state):
                        state = pd.concat([state, own.drop(columns=["track_id", "position_timestamp", "created_at"])], axis=1)
            fused = fused.sort_values("created_at", kind="stable").reset_index(drop=True)
            if state is not None:
                # the strategy's numbers about a track, on the fused plot of the same track and position time
                keys = ["track_id", "position_timestamp", "created_at"]
                fused = fused.merge(state.drop_duplicates(keys, keep="last"), on=keys, how="left", suffixes=("", "_state"))
            self.runs[run_id] = (fused, outcomes, state)
        return self.runs[run_id]

    def run(self, run_id: str) -> dict:
        """The base columns of a strategy's fused plots, sorted by when they were emitted, plus its fields."""
        fused, _, state = self.load_run(run_id)
        # the strategy's own state (state_...) stays here, for predict(); the page gets the numbers meant for people
        state_columns = [] if state is None else [c for c in state.columns if c not in ("track_id", "position_timestamp", "created_at") and not c.startswith(STATE_PREFIX)]
        base = dict(track=fused["track_id"], created=self.ms(fused["created_at"]), valid_to=self.ms(fused["valid_to"]),
                    t=self.ms(fused["position_timestamp"]), r=self.ms(fused["asi_received_timestamp"]), src=number(fused, "source_identifier"),
                    lat=number(fused, "latitude"), lon=number(fused, "longitude"), alt=number(fused, "altitude_ft"), gs=number(fused, "ground_speed_kt"), trk=number(fused, "track_deg"),
                    cs=fused["callsign"], hex=fused["adshex"], tail=fused["tail_number"], quality=fused["quality"],
                    **{c: fused[c] for c in state_columns})
        fields = schema(fused.drop(columns=state_columns), {"event", "track_id"}, fused_docs(), NOTES.get("fused"))
        fields += [dict(field, table="track_state") for field in schema(fused[state_columns], set(), None, NOTES.get("fused"))]
        return dict(**{k: jsonable(v) for k, v in base.items()}, state_columns=state_columns, schema=fields)

    def predict(self, run_id: str, i: int, seconds: list[float]) -> dict:
        """Where the strategy expects the aircraft some seconds after its fused plot i (in the page's order), by its own
        predict() from the state it recorded there; nothing when it has no predict or recorded no state for that plot."""
        strategy = STRATEGIES.get(run_id.split("/")[0])
        fused, _, _ = self.load_run(run_id)
        own = [c for c in fused.columns if c.startswith(STATE_PREFIX)]
        if not hasattr(strategy, "predict") or not own or not 0 <= i < len(fused) or fused.loc[i, own].isna().any():
            return dict(ellipses=[])
        state = {c: float(fused.loc[i, c]) for c in own}
        params = next(r for r in self.run_list() if r["id"] == run_id).get("params") or {}
        return dict(ellipses=[dict(seconds=t, **strategy.predict(state, t, params)) for t in seconds])

    def run_field(self, run_id: str, column: str) -> dict | None:
        fused, _, _ = self.load_run(run_id)
        if column not in fused.columns:
            return None
        return field_payload(*classify(fused[column]))

    def outcomes(self, run_id: str) -> dict:
        """What the strategy did with every raw plot, lined up with the page's raw plots, and its recorded numbers."""
        _, outcomes, _ = self.load_run(run_id)
        page = self.raw_order.merge(outcomes.rename(columns={"source": "src"}), on=["src", "row"], how="left")
        numbers = [c for c in outcomes.columns if c not in ("source", "row", "state", "track_id", "reason")]
        return dict(state=jsonable(page["state"].fillna("unknown")), track=jsonable(page["track_id"]), reason=jsonable(page["reason"]),
                    numbers={c: jsonable(page[c]) for c in numbers})


def plot_kind(f: pd.DataFrame, source: str) -> pd.Series:
    """The kind of plot inside a source, as words, or empty when the source has only one kind."""
    if source == "adsbx" and "type" in f.columns:
        return pd.to_numeric(f["type"], errors="coerce").map(ADSBX_KIND).fillna("")
    if source == "planefinder" and "data_source" in f.columns:
        return pd.to_numeric(f["data_source"], errors="coerce").map(PLANEFINDER_KIND).fillna("")
    return pd.Series([""] * len(f))


def on_ground(f: pd.DataFrame, source: str) -> pd.Series:
    """On the ground, as the source says it: ADS-B Exchange writes "ground" into alt_baro, uAvionix sets the ground bit."""
    if source == "adsbx" and "alt_baro" in f.columns:
        return (f["alt_baro"].astype("string") == "ground").fillna(False).astype(int)
    if source == "uavionix" and "target_report_descriptor.is_ground_bit_set" in f.columns:
        return (f["target_report_descriptor.is_ground_bit_set"].astype("string").str.lower() == "true").fillna(False).astype(int)
    return pd.Series([0] * len(f))


def fused_docs() -> dict[str, str]:
    """What each fused plot column means: the FusedPlot proto comments (its Common block flattened as run.py does),
    the event and segment fields, and the columns the harness adds."""
    docs = {name.split(".")[-1]: doc for name, doc in protodocs.flat("uni.protobuf.uni_track_schemas.fusion.v1beta.FusedPlot").items() if doc}
    event = protodocs.messages().get("uni.protobuf.uni_track_schemas.fusion.v1beta.FusionChangedEvent", {})
    segment = protodocs.messages().get("uni.protobuf.uni_track_schemas.fusion.v1beta.ChangedSegment", {})
    docs.update({name: event[name][0] for name in ("track_id", "created_at", "quality") if name in event})
    docs.update({name: segment[name][0] for name in ("since", "until") if name in segment})
    docs.update(valid_to="Added by the harness: created_at of the first later event on the same track that covers this plot's position time, so the time this version stopped being current. Empty when nothing replaced it.")
    return docs


def list_cases(root: pathlib.Path) -> list[dict]:
    out = []
    for folder in sorted(p for p in root.iterdir() if (p / "case.json").exists()):
        info = json.loads((folder / "case.json").read_text())
        complete = (folder / "raw").exists() and any((folder / "raw").glob("*.parquet"))
        out.append(dict(name=folder.name, complete=complete, t_start=info.get("t_start"), suspect=(info.get("suspect") or {}).get("callsign")))
    return out


def make_handler(root: pathlib.Path):
    cases: dict[str, Case] = {}
    lock = threading.Lock()   # one request at a time loads case data; static files are served alongside

    def open_case(name: str) -> Case:
        if name not in cases:
            cases[name] = Case(root / name)
        return cases[name]

    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self):
            # the page changes often while we work on it; never let the browser keep an old copy
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                self.path = "/viewer.html"
                return SimpleHTTPRequestHandler.do_GET(self)
            if not url.path.startswith("/api/"):
                return SimpleHTTPRequestHandler.do_GET(self)
            try:
                with lock:
                    answer = self._api(url.path[len("/api/"):], {k: v[0] for k, v in parse_qs(url.query).items()})
                # a job still running in the background is waited for here, after the lock, so other requests go on
                if isinstance(answer, Future):
                    return self._json(answer.result())
            except (FileNotFoundError, KeyError) as error:
                return self._json(dict(error=f"not found: {error}"), 404)
            except Exception as error:
                return self._json(dict(error=f"{type(error).__name__}: {error}"), 500)

        def _api(self, what: str, q: dict) -> Future | None:
            if what == "cases":
                return self._json(dict(cases=list_cases(root)))
            if "case" not in q or not (root / q["case"] / "case.json").exists():
                return self._json(dict(error="no such case"), 404)
            case = open_case(q["case"])
            known = {r["id"] for r in case.run_list()}
            if "run" in q and q["run"] not in known:
                return self._json(dict(error="no such strategy run"), 404)
            if case.raw_order is None and what != "case":
                case.raw()   # the page's raw order is needed to line up outcomes and fields
            if what == "case":
                return self._json(dict(case=case.info, t0_us=case.t0_us, span_ms=(case.t1_us - case.t0_us) // 1000, runs=case.run_list(), notes=NOTES.get("fused", {})))
            if what == "raw":
                return self._json(case.raw())
            if what == "schema":
                return case.schema_job
            if what == "predict":
                if "run" not in q or not q.get("i", "").isdigit():
                    return self._json(dict(error="a prediction needs a run and a plot number"), 400)
                return self._json(case.predict(q["run"], int(q["i"]), [float(t) for t in q.get("seconds", "5,10,20,30,60").split(",")]))
            if what == "run":
                return self._json(case.run(q["run"]))
            if what == "outcomes":
                return self._json(case.outcomes(q["run"]))
            if what == "field" and not q.get("column"):
                return self._json(dict(error="a field request needs a column"), 400)
            if what == "field" and q.get("source"):
                return self._json(case.raw_field(q["source"], q["column"]) or dict(kind="number", values=None, words=None))
            if what == "field" and q.get("run"):
                return self._json(case.run_field(q["run"], q["column"]) or dict(kind="number", values=None, words=None))
            return self._json(dict(error="not found"), 404)

        def do_POST(self):
            # the one thing the page may write: the note of a run, into its run.json
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if self.headers.get("Origin") not in (None, f"http://localhost:{self.server.server_port}", f"http://127.0.0.1:{self.server.server_port}"):
                return self._json(dict(error="notes are only written from the viewer's own page"), 403)
            if url.path == "/api/note" and (root / q.get("case", "") / "case.json").exists():
                runs = {r["id"] for r in open_case(q["case"]).run_list() if not r.get("production")}
                if q.get("run") not in runs:
                    return self._json(dict(error="no such strategy run"), 404)
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
                strategy, label = q["run"].split("/", 1)
                try:
                    manifest = runbook.set_note(root / q["case"], strategy, label, str(body.get("note", ""))[:2000])
                except FileNotFoundError:
                    return self._json(dict(error="no such run"), 404)
                return self._json(manifest)
            return self._json(dict(error="not found"), 404)

        def log_message(self, *a):
            pass

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(pathlib.Path.cwd() / "data" / "cases"), help="folder with one sub folder per case")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    a = ap.parse_args()
    root = pathlib.Path(a.cases).resolve()
    if not root.is_dir():
        raise SystemExit(f"no such folder: {root}")
    os.chdir(HERE)
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(root))
    print(f"viewer: http://localhost:{a.port}  (ctrl-c to stop)")
    if not a.no_browser:
        webbrowser.open(f"http://localhost:{a.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
