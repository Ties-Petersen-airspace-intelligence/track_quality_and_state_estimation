"""Local viewer for one case: raw plots underneath, strategy runs replayed on top.

usage: uv run -m harness.viewer.server --case data/cases/<name> [--port 8770]
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
        )))
    frame = pd.concat(parts, ignore_index=True).sort_values("r").reset_index(drop=True)
    return columnar(frame)


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


def make_handler(case: pathlib.Path):
    info = json.loads((case / "case.json").read_text())
    t0_us = int(pd.Timestamp(info["t_start"], tz="UTC").timestamp() * 1e6)
    t1_us = int(pd.Timestamp(info["t_end"], tz="UTC").timestamp() * 1e6)
    runs = sorted(p.name for p in (case / "runs").glob("*") if (p / "fused_plots.parquet").exists()) if (case / "runs").exists() else []
    cache = {}

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
            if self.path in ("/", "/index.html"):
                self.path = "/viewer.html"
                return SimpleHTTPRequestHandler.do_GET(self)
            if self.path == "/api/case":
                return self._json(dict(case=info, t0_us=t0_us, span_ms=(t1_us - t0_us) // 1000, runs=runs))
            if self.path == "/api/raw":
                cache.setdefault("raw", load_raw(case, t0_us))
                return self._json(cache["raw"])
            if self.path.startswith("/api/run/"):
                name = self.path.split("/")[-1]
                if name not in runs:
                    return self._json(dict(error="no such run"), 404)
                cache.setdefault(name, load_run(case, name, t0_us))
                return self._json(cache[name])
            return SimpleHTTPRequestHandler.do_GET(self)

        def log_message(self, *a):
            pass

    return H


def main():
    import os
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--port", type=int, default=8770)
    a = ap.parse_args()
    case = pathlib.Path(a.case).resolve()
    os.chdir(HERE)
    srv = HTTPServer(("127.0.0.1", a.port), make_handler(case))
    print(f"viewer: http://localhost:{a.port}  (ctrl-c to stop)")
    webbrowser.open(f"http://localhost:{a.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
