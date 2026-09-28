"""One case's suspect aircraft: its raw plots as RawPlots (only that hex, so a run takes seconds), its production tracks, and
the case's own description of what went wrong. Loaded once per case and cached under experiments/cache/ as a pickle."""
from __future__ import annotations

import json, pathlib, pickle

import pandas as pd

from harness.raw_plots import RawPlot, SOURCE_MESSAGE, fill_message

CACHE = pathlib.Path(__file__).parent / "cache"
CASES = pathlib.Path(__file__).parent.parent / "data" / "cases"


def case_folders() -> list[pathlib.Path]:
    return sorted(p for p in CASES.iterdir() if (p / "case.json").exists())


def load(case: pathlib.Path, hex: str | None = None) -> dict:
    """info (case.json), plots (the raw plots of one aircraft in receipt order: the suspect, or the hex given), append and
    regular (production's tracks for that hex)."""
    CACHE.mkdir(exist_ok=True)
    info = json.loads((case / "case.json").read_text())
    hex = (hex or info["suspect"]["hex"]).upper()
    cached = CACHE / f"{case.name}{'' if hex == info['suspect']['hex'].upper() else '-' + hex}.pickle"
    if cached.exists():
        return pickle.loads(cached.read_bytes())
    if hex != info["suspect"]["hex"].upper():
        info = {**info, "name": f"{info['name']} {hex}", "suspect": {"hex": hex, "callsign": ""}, "event": None, "reason": f"aircraft {hex} of this case"}
    out = dict(info=info, plots=suspect_plots(case, hex), append=production(case, "append", hex), regular=production(case, "final", hex))
    cached.write_bytes(pickle.dumps(out))
    return out


def suspect_plots(case: pathlib.Path, hex: str) -> list[RawPlot]:
    """The raw plots whose common.adshex is the suspect's, built into protos the same way harness.raw_plots does, with their
    original row numbers, sorted by receipt time."""
    plots = []
    for source, message_class in SOURCE_MESSAGE.items():
        path = case / "raw" / f"{source}.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        if frame.empty or "common.adshex" not in frame.columns:
            continue
        frame = frame[frame["common.adshex"].astype(str).str.upper() == hex.upper()]
        columns = set(frame.columns)
        for number, row in zip(frame.index, frame.to_dict("records")):
            message = message_class()
            fill_message(message, row, columns, "")
            plots.append(RawPlot(source, int(number), message.common.asi_received_timestamp, message.common.position_timestamp, message))
    plots.sort(key=lambda p: (p.received_us, p.position_us))
    return plots


def production(case: pathlib.Path, part: str, hex: str) -> pd.DataFrame:
    """Production's fused plots for the hex: position time (us), lat, lon, altitude_ft, ground_speed_kt, source_identifier, and for
    the final table valid_to (us), so the last version of each plot can be picked."""
    f = pd.read_parquet(case / "production" / f"{part}.parquet")
    f = f[f["adshex"].astype(str).str.upper() == hex.upper()]
    out = pd.DataFrame(dict(position_us=pd.to_numeric(f["position_timestamp_us"], errors="coerce"),
                            lat=pd.to_numeric(f["latitude"], errors="coerce"), lon=pd.to_numeric(f["longitude"], errors="coerce"),
                            altitude_ft=pd.to_numeric(f["altitude_ft"], errors="coerce"), ground_speed_kt=pd.to_numeric(f["ground_speed_kt"], errors="coerce"),
                            source_identifier=pd.to_numeric(f["source_identifier"], errors="coerce")))
    if part == "final":
        out["valid_to"] = pd.to_numeric(f["valid_to_us"], errors="coerce")
        out = out[out["valid_to"].isna()]        # the version that was still current when the case was pulled
    return out.dropna(subset=["position_us", "lat", "lon"]).sort_values("position_us").reset_index(drop=True)
