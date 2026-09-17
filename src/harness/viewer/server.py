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
            _pos_us=micros("position_timestamp").astype("Int64"),
        )))
    frame = pd.concat(parts, ignore_index=True).sort_values("r").reset_index(drop=True)
    out = columnar(frame.drop(columns=["_pos_us"]))
    out["_pos_us"] = frame["_pos_us"].tolist(); out["_t0_us"] = t0_us   # server side only, stripped before sending
    return out


def load_run(case: pathlib.Path, name: str, t0_us: int) -> dict:
    f = pd.read_parquet(case / "runs" / name / "fused_plots.parquet")
    frame = pd.DataFrame(dict(
        track=f["track_id"], created=(f["created_at_us"] - t0_us) // 1000,
        valid_to=((f["valid_to_us"] - t0_us) // 1000) if "valid_to_us" in f else None,
        t=(f["position_us"] - t0_us) // 1000, r=(f["asi_received_us"] - t0_us) // 1000,
        src=f["source_identifier"], lat=f["latitude"], lon=f["longitude"], alt=f["altitude_ft"], gs=f["ground_speed_kt"],
        trk=f["track_deg"], hdg=f["heading_deg"], cs=f["callsign"], hex=f["adshex"], tail=f["tail_number"], quality=f["quality"],
    )).sort_values("created").reset_index(drop=True)
    return columnar(frame)


def load_used(case: pathlib.Path, name: str, raw: dict) -> dict:
    """For every raw plot, in the page's raw order: the strategy track that took it, "" if the strategy
    used it without saying which track, or None if it was dropped."""
    path = case / "runs" / name / "used_raw.parquet"
    if not path.exists():
        return dict(track=None)
    used = pd.read_parquet(path)
    key = list(zip(used["source"], pd.to_numeric(used["position_us"]).astype("Int64").tolist(), used["source_track_identifier"].fillna("")))
    lookup = dict(zip(key, used["track_id"].tolist()))
    t0 = raw["_t0_us"]
    out = []
    for src, t_ms, tid, pos_us in zip(raw["src"], raw["t"], raw["tid"], raw["_pos_us"]):
        v = lookup.get((src, pos_us, tid), None)
        out.append(None if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA else v)
    return dict(track=out)


def list_cases(root: pathlib.Path) -> list[dict]:
    out = []
    for folder in sorted(p for p in root.iterdir() if (p / "case.json").exists()):
        runs = sorted(r.name for r in (folder / "runs").glob("*") if (r / "fused_plots.parquet").exists()) if (folder / "runs").exists() else []
        info = json.loads((folder / "case.json").read_text())
        out.append(dict(name=folder.name, complete=bool(runs), runs=runs, t_start=info.get("t_start"), suspect=(info.get("suspect") or {}).get("callsign")))
    return out


def make_handler(root: pathlib.Path):
    cache = {}   # case name -> dict(info, t0_us, t1_us, runs, raw, run data, used data)

    def open_case(name: str) -> dict:
        if name in cache:
            return cache[name]
        case = root / name
        info = json.loads((case / "case.json").read_text())
        t0_us = int(pd.Timestamp(info["t_start"], tz="UTC").timestamp() * 1e6)
        t1_us = int(pd.Timestamp(info["t_end"], tz="UTC").timestamp() * 1e6)
        runs = sorted(p.name for p in (case / "runs").glob("*") if (p / "fused_plots.parquet").exists()) if (case / "runs").exists() else []
        cache[name] = dict(path=case, info=info, t0_us=t0_us, t1_us=t1_us, runs=runs, data={})
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
                    return self._json(dict(case=c["info"], t0_us=c["t0_us"], span_ms=(c["t1_us"] - c["t0_us"]) // 1000, runs=c["runs"]))
                if kind == "raw":
                    c["data"].setdefault("raw", load_raw(c["path"], c["t0_us"]))
                    return self._json({k: v for k, v in c["data"]["raw"].items() if not k.startswith("_")})
                if kind in ("run", "used") and len(parts) == 4:
                    run = parts[3]
                    if run not in c["runs"]:
                        return self._json(dict(error="no such strategy"), 404)
                    if kind == "run":
                        c["data"].setdefault("run:" + run, load_run(c["path"], run, c["t0_us"]))
                        return self._json(c["data"]["run:" + run])
                    c["data"].setdefault("raw", load_raw(c["path"], c["t0_us"]))
                    c["data"].setdefault("used:" + run, load_used(c["path"], run, c["data"]["raw"]))
                    return self._json(c["data"]["used:" + run])
            return SimpleHTTPRequestHandler.do_GET(self)

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
