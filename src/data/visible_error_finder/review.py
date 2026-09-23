"""Step 6: a local page with one card per shortlisted candidate; press good or bad, marks go to marks.json.

usage: uv run data/visible_error_finder/review.py [--list shortlist] [--port 8771]

Shows out/<list>.json with live maps and charts per candidate, fed from out/<day>/plots.parquet.
Marks go to out/marks.json for the shortlist and to out/marks_<list>.json for any other list.
Open http://localhost:8771. Run from src/.
"""
import argparse, functools, http.server, json, math, pathlib, types

import pandas as pd

from draw import SOURCE_COLOUR, SOURCE_NAME, implied_speed_kt, main_track
from sets import path

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"
LIST = "shortlist"
MARKS = OUT / "marks.json"


@functools.cache
def plots_of_day(day: str, name: str) -> dict:
    return dict(tuple(pd.read_parquet(path(OUT / day, "plots", name)).groupby("id")))


@functools.cache
def shortlist_by_id() -> dict:
    return {item["id"]: item for item in json.loads((OUT / f"{LIST}.json").read_text())}


def clean(values) -> list:
    """JSON has no NaN."""
    return [None if v is None or (isinstance(v, float) and math.isnan(v)) else v for v in values]


def candidate_plots(candidate_id: str) -> dict:
    """The track shown for each fusion, as columns, plus the event."""
    item = shortlist_by_id()[candidate_id]
    plots = plots_of_day(item["day"], item.get("set", "")).get(candidate_id)
    candidate = types.SimpleNamespace(**item)
    tracks = {}
    for fusion in ("append", "regular"):
        track = main_track(plots[plots.fusion == fusion], candidate) if plots is not None else pd.DataFrame()
        if track.empty:
            tracks[fusion] = None
            continue
        tracks[fusion] = dict(
            tid=track.tid.iloc[0], t=clean(track.t.round(3).tolist()), lat=clean(track.lat.tolist()), lon=clean(track.lon.tolist()),
            alt=clean(track.alt.astype(float).tolist()), gs=clean(track.gs.astype(float).tolist()), trk=clean(track.trk.astype(float).tolist()),
            implied=clean([round(v, 1) for v in implied_speed_kt(track).tolist()]), src=track.src.astype(int).tolist())
    sources = {int(k): dict(name=SOURCE_NAME[k], colour=SOURCE_COLOUR.get(k, "#444444")) for k in SOURCE_NAME}
    return dict(tracks=tracks, sources=sources,
                event=dict(t=item["t_event"], lat=item["lat"], lon=item["lon"], plat=item.get("plat"), plon=item.get("plon")))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def do_GET(self):
        if self.path == "/marks":
            return self.send_json(json.loads(MARKS.read_text()) if MARKS.exists() else {})
        if self.path.startswith("/plots/"):
            return self.send_json(candidate_plots(self.path.removeprefix("/plots/")))
        if self.path == "/shortlist":
            return self.send_json(json.loads((OUT / f"{LIST}.json").read_text()))
        if self.path == "/":
            self.path = "/review.html"
        return super().do_GET()

    def do_POST(self):
        # one mark: {"id": ..., "mark": "good" | "bad" | "", "note": ...}
        mark = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        marks = json.loads(MARKS.read_text()) if MARKS.exists() else {}
        marks[mark["id"]] = {"mark": mark["mark"], "note": mark.get("note", "")}
        MARKS.write_text(json.dumps(marks, indent=1))
        self.send_json({"ok": True})

    def send_json(self, value):
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--list", default="shortlist")
    args = parser.parse_args()
    global LIST, MARKS
    LIST = args.list
    MARKS = OUT / ("marks.json" if LIST == "shortlist" else f"marks_{LIST}.json")
    print(f"http://localhost:{args.port}")
    http.server.ThreadingHTTPServer(("localhost", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
