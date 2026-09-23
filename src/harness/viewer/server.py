"""Local viewer: raw plots underneath, strategy output replayed on top, one case at a time.

usage: uv run -m harness.viewer.server [--cases data/cases] [--port 8770]

Every folder under --cases with a case.json is a case. A case is complete when it has at least one
strategy output under runs/; incomplete ones are listed but cannot be opened.
"""
from __future__ import annotations

import argparse, json, pathlib, webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

import numpy as np
import pandas as pd

from .. import runs as runbook

HERE = pathlib.Path(__file__).parent
RAW_SOURCES = ["adsbx", "planefinder", "uavionix", "stdds", "tfms_ti", "tfms_or", "ual", "asa"]


def columnar(frame: pd.DataFrame) -> dict:
    """Column arrays, nulls as None, so the page gets one array per field instead of one object per row."""
    out = {}
    for c in frame.columns:
        s = frame[c]
        if pd.api.types.is_numeric_dtype(s):
            out[c] = [None if pd.isna(v) else (int(v) if float(v).is_integer() else round(float(v), 6)) for v in s.tolist()]
        else:
            out[c] = ["" if pd.isna(v) else str(v) for v in s.tolist()]
    return out


def num(f: pd.DataFrame, col: str | None) -> pd.Series:
    """A numeric column, or all missing when the source has no such field."""
    if col is None or col not in f.columns:
        return pd.Series([None] * len(f), dtype="Float64")
    return pd.to_numeric(f[col], errors="coerce")


ADSBX_TYPE = {1: "ADS-B", 2: "ADS-B, no position in message", 3: "ADS-R", 4: "TIS-B", 5: "TIS-B track file", 6: "ADS-C", 7: "MLAT", 8: "Mode S only", 9: "ADS-B other", 10: "ADS-R other", 11: "TIS-B other", 12: "other"}
PF_SOURCE = {1: "ADS-B", 2: "PlaneFinder MLAT", 3: "FLARM", 4: "third party MLAT", 5: "blocked"}


def plot_kind(f: pd.DataFrame, source: str) -> pd.Series:
    """The kind of plot inside a source, as words, or empty when the source has only one kind."""
    if source == "adsbx" and "type" in f.columns:
        return pd.to_numeric(f["type"], errors="coerce").map(ADSBX_TYPE).fillna("")
    if source == "planefinder" and "data_source" in f.columns:
        return pd.to_numeric(f["data_source"], errors="coerce").map(PF_SOURCE).fillna("")
    return pd.Series([""] * len(f))


def load_raw(case: pathlib.Path, t0_us: int) -> dict:
    parts = []
    for source in RAW_SOURCES:
        path = case / f"{source}.parquet"
        if not path.exists():
            continue
        f = pd.read_parquet(path)
        if f.empty:
            continue
        c = lambda name: f[name] if name in f.columns else pd.Series([None] * len(f))
        # common timestamps: the exact recovered column when the table had a TIMESTAMP, else the source's own int64 micros
        micros = lambda base: pd.to_numeric(f[f"common_{base}_us"] if f"common_{base}_us" in f.columns else f[f"common.{base}"], errors="coerce")
        parts.append(pd.DataFrame(dict(
            src=source,
            t=(micros("position_timestamp") - t0_us) // 1000,      # ms after the case start, position time
            r=(micros("asi_received_timestamp") - t0_us) // 1000,  # ms after the case start, when we received it
            lat=pd.to_numeric(c("common.latitude")), lon=pd.to_numeric(c("common.longitude")),
            alt=pd.to_numeric(c("common.altitude_ft"), errors="coerce"), gs=pd.to_numeric(c("common.ground_speed_kt"), errors="coerce"),
            trk=pd.to_numeric(c("common.track_deg"), errors="coerce"), hdg=pd.to_numeric(c("common.heading_deg"), errors="coerce"),
            cs=c("common.callsign"), hex=c("common.adshex"), tail=c("common.tail_number"), tid=c("common.track_identifier"),
            # ADS-B accuracy numbers where the source carries them: NACp, NIC, Rc in metres, NACv, SIL
            nacp=num(f, {"adsbx": "nac_p", "uavionix": "quality_indicators.nacp", "stdds": "status.nacp"}.get(source)),
            nic=num(f, {"adsbx": "nic", "uavionix": "quality_indicators.nucp_or_nic", "stdds": "status.nic"}.get(source)),
            rc=num(f, {"adsbx": "rc"}.get(source)),
            # the two kinds of altitude a source carries in its own fields; common.altitude_ft is the barometric one for every source
            alt_baro=(num(f, "flight_level") * 100 if source == "uavionix" else num(f, {"adsbx": "alt_baro", "planefinder": "altitude", "tfms_ti": "common.altitude_ft", "tfms_or": "common.altitude_ft", "ual": "common.altitude_ft", "asa": "common.altitude_ft"}.get(source))),
            alt_geo=num(f, {"adsbx": "alt_geom", "uavionix": "geometric_height"}.get(source)),
            nacv=num(f, {"adsbx": "nac_v", "uavionix": "quality_indicators.nucr_or_nacv"}.get(source)),
            sil=num(f, {"adsbx": "sil", "uavionix": "quality_indicators.sil", "stdds": "status.sil"}.get(source)),
            # the kind of plot inside the source: ADS-B Exchange's type, PlaneFinder's data_source; empty when the source has only one kind
            kind=plot_kind(f, source),
            _pos_us=micros("position_timestamp").astype("Int64"),
            # on the ground, as the source says it: ADS-B Exchange writes "ground" into alt_baro, uAvionix sets the ground bit
            ground=((c("alt_baro").astype("string") == "ground") if source == "adsbx" else (c("target_report_descriptor.is_ground_bit_set").astype("string").str.lower() == "true") if source == "uavionix" else pd.Series([False] * len(f))).fillna(False).astype(int),
        )))
    frame = pd.concat(parts, ignore_index=True).sort_values("r").reset_index(drop=True)
    out = columnar(frame.drop(columns=["_pos_us"]))
    out["_pos_us"] = [int(v) if pd.notna(v) else None for v in (frame["_pos_us"] if "_pos_us" in frame else [])]
    out["_t0_us"] = t0_us   # server side only, stripped before sending
    return out


def load_run(case: pathlib.Path, name: str, t0_us: int) -> dict:
    """name is 'strategy/label', the run's folder under runs/."""
    f = pd.read_parquet(case / "runs" / name / "fused_plots.parquet")
    frame = pd.DataFrame(dict(
        track=f["track_id"], created=(f["created_at_us"] - t0_us) // 1000,
        valid_to=((f["valid_to_us"] - t0_us) // 1000) if "valid_to_us" in f else None,
        t=(f["position_us"] - t0_us) // 1000, r=(f["asi_received_us"] - t0_us) // 1000,
        src=f["source_identifier"], lat=f["latitude"], lon=f["longitude"], alt=f["altitude_ft"], gs=f["ground_speed_kt"],
        trk=f["track_deg"], hdg=f["heading_deg"], cs=f["callsign"], hex=f["adshex"], tail=f["tail_number"], quality=f["quality"],
        # whatever the strategy added, for example sigma_horizontal_m; a run without them has no such columns
        **{c: f[c] for c in f.columns if c.startswith("sigma_")},
    )).sort_values("created").reset_index(drop=True)
    return columnar(frame)


def load_outcomes(case: pathlib.Path, name: str, raw: dict) -> dict:
    """For every raw plot, in the page's raw order: the state the strategy gave it, the track it went into and the
    reason. A run without raw_outcomes.parquet (made before outcomes existed) answers with nulls."""
    path = case / "runs" / name / "raw_outcomes.parquet"
    if not path.exists():
        return dict(state=None, track=None, reason=None)
    o = pd.read_parquet(path)
    key = list(zip(o["source"], pd.to_numeric(o["position_us"]).astype("Int64").tolist(), o["source_track_identifier"].fillna("")))
    lookup = dict(zip(key, zip(o["state"], o["track_id"].astype("string").fillna(""), o["reason"].fillna(""))))
    state, track, reason = [], [], []
    for src, pos_us, tid in zip(raw["src"], raw["_pos_us"], raw["tid"]):
        v = lookup.get((src, pos_us, tid))
        state.append(v[0] if v else None); track.append(v[1] if v else None); reason.append(v[2] if v else None)
    return dict(state=state, track=track, reason=reason)


def list_cases(root: pathlib.Path) -> list[dict]:
    out = []
    for folder in sorted(p for p in root.iterdir() if (p / "case.json").exists()):
        runs = [r["id"] for r in runbook.list_runs(folder)]
        info = json.loads((folder / "case.json").read_text())
        out.append(dict(name=folder.name, complete=bool(runs), runs=runs, t_start=info.get("t_start"), suspect=(info.get("suspect") or {}).get("callsign")))
    return out


def make_handler(root: pathlib.Path):
    cache = {}   # case name -> dict(info, t0_us, t1_us, runs, raw, run data)

    def open_case(name: str) -> dict:
        if name in cache:
            return cache[name]
        case = root / name
        info = json.loads((case / "case.json").read_text())
        t0_us = int(pd.Timestamp(info["t_start"], tz="UTC").timestamp() * 1e6)
        t1_us = int(pd.Timestamp(info["t_end"], tz="UTC").timestamp() * 1e6)
        cache[name] = dict(path=case, info=info, t0_us=t0_us, t1_us=t1_us, runs=runbook.list_runs(case), data={})
        return cache[name]

    class H(SimpleHTTPRequestHandler):
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
            if self.path in ("/", "/index.html") or self.path.startswith("/?"):
                self.path = "/viewer.html"
                return SimpleHTTPRequestHandler.do_GET(self)
            parts = [p for p in self.path.split("?")[0].split("/") if p]
            if parts == ["api", "cases"]:
                return self._json(dict(cases=list_cases(root)))
            if len(parts) >= 3 and parts[0] == "api":
                kind, name = parts[1], parts[2]
                if not (root / name / "case.json").exists():
                    return self._json(dict(error="no such case"), 404)
                c = open_case(name)
                if kind == "case":
                    c["runs"] = runbook.list_runs(c["path"])   # a run may have been added since the case was first opened
                    return self._json(dict(case=c["info"], t0_us=c["t0_us"], span_ms=(c["t1_us"] - c["t0_us"]) // 1000, runs=c["runs"]))
                if kind == "raw":
                    c["data"].setdefault("raw", load_raw(c["path"], c["t0_us"]))
                    return self._json({k: v for k, v in c["data"]["raw"].items() if not k.startswith("_")})
                if kind in ("run", "outcomes") and len(parts) == 5:
                    run = parts[3] + "/" + parts[4]
                    if run not in [r["id"] for r in c["runs"]]:
                        return self._json(dict(error="no such strategy"), 404)
                    if kind == "run":
                        c["data"].setdefault("run:" + run, load_run(c["path"], run, c["t0_us"]))
                        return self._json(c["data"]["run:" + run])
                    c["data"].setdefault("raw", load_raw(c["path"], c["t0_us"]))
                    c["data"].setdefault("outcomes:" + run, load_outcomes(c["path"], run, c["data"]["raw"]))
                    return self._json(c["data"]["outcomes:" + run])
            return SimpleHTTPRequestHandler.do_GET(self)

        def do_POST(self):
            # the one thing the page may write: the note of a run, into its run.json
            parts = [p for p in self.path.split("?")[0].split("/") if p]
            if len(parts) == 5 and parts[:2] == ["api", "note"] and (root / parts[2] / "case.json").exists():
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
                try:
                    manifest = runbook.set_note(root / parts[2], parts[3], parts[4], str(body.get("note", ""))[:2000])
                except FileNotFoundError:
                    return self._json(dict(error="no such run"), 404)
                if parts[2] in cache:
                    cache[parts[2]]["runs"] = runbook.list_runs(root / parts[2])
                return self._json(manifest)
            return self._json(dict(error="not found"), 404)

        def log_message(self, *a):
            pass

    return H


def main():
    import os
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(pathlib.Path.cwd() / "data" / "cases"), help="folder with one sub folder per case")
    ap.add_argument("--port", type=int, default=8770)
    a = ap.parse_args()
    root = pathlib.Path(a.cases).resolve()
    if not root.is_dir():
        raise SystemExit(f"no such folder: {root}")
    os.chdir(HERE)
    srv = HTTPServer(("127.0.0.1", a.port), make_handler(root))
    print(f"viewer: http://localhost:{a.port}  (ctrl-c to stop)")
    webbrowser.open(f"http://localhost:{a.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
