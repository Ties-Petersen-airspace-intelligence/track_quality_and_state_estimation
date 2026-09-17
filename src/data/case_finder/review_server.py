"""Serve the case review page and save good/bad marks into cases.json.

usage: python review_server.py --day 2026-09-16 [--port 8765]
then open http://localhost:8765
"""
import argparse, json, pathlib, webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler

HERE = pathlib.Path(__file__).parent


def make_handler(day):
    out = HERE / "out" / day
    cases_file = out / "cases.json"

    class H(SimpleHTTPRequestHandler):
        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                self.path = "/review.html"
                return SimpleHTTPRequestHandler.do_GET(self)
            if self.path == "/api/cases":
                return self._json(dict(day=day, cases=json.loads(cases_file.read_text())))
            if self.path.startswith("/api/case/"):
                f = out / "cases" / (self.path.split("/")[-1] + ".json")
                if not f.exists():
                    return self._json(dict(error="no plots pulled for this case yet, run pull_case_plots.py"), 404)
                return self._json(json.loads(f.read_text()))
            return SimpleHTTPRequestHandler.do_GET(self)

        def do_POST(self):
            if self.path != "/api/mark":
                return self._json(dict(error="unknown"), 404)
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            cases = json.loads(cases_file.read_text())
            for c in cases:
                if c["id"] == body["id"]:
                    c["mark"] = body.get("mark")
                    c["note"] = body.get("note", c.get("note", ""))
            cases_file.write_text(json.dumps(cases, indent=1))
            return self._json(dict(ok=True))

        def log_message(self, *a):
            pass

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", required=True)
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    import os
    os.chdir(HERE)
    srv = HTTPServer(("127.0.0.1", a.port), make_handler(a.day))
    print(f"review page: http://localhost:{a.port}   (ctrl-c to stop)")
    webbrowser.open(f"http://localhost:{a.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
