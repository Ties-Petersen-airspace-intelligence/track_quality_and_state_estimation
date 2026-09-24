"""How accurate is each source, measured from the test cases without any ground truth.

Ways of measuring, all on the raw plots in the case folders:
1. against a reference source (uAvionix, or ADS-B Exchange where uAvionix has no coverage):
   where the reference says the aircraft was at the exact time of the plot, split into metres
   along the direction of flight and across it. Along divided by speed is a time offset.
2. three cornered hat between ADS-B Exchange, uAvionix and PlaneFinder: each source's own scatter.
3. against itself: scatter around a straight line through 9 of one source's own plots.
Plus: lateness (received minus position time), coverage of the accuracy fields, and how they vary by case.

usage: uv run src/analysis/source_accuracy.py [--cases src/data/cases] [--out <folder>]
Writes source_accuracy.json, a few parquet files with the matched plots, and PNG charts.
"""
from __future__ import annotations

import argparse, json, pathlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SOURCES = ["adsbx", "uavionix", "planefinder", "tfms_ti"]
ADSBX_TYPE = {1: "adsb", 2: "adsb", 3: "adsr", 4: "tisb", 5: "tisb", 6: "adsc", 7: "mlat", 8: "mode_s", 9: "adsb", 10: "adsr", 11: "tisb", 12: "other"}
PF_SOURCE = {1: "adsb", 2: "mlat", 3: "flarm", 4: "mlat", 5: "blocked"}
MAX_GAP_S = 4.0          # reference plots must bracket the plot this closely
MIN_SPEED = 60.0         # m/s, below this along track offsets cannot be read as time
CROSS_MIN_SPEED = 30.0   # m/s, below this the direction of flight is not well defined


def num(s):
    return pd.to_numeric(s, errors="coerce")


def load(case: pathlib.Path) -> pd.DataFrame:
    """Every raw plot of the case in one frame with exact times and the accuracy numbers each source has."""
    parts = []
    for src in SOURCES:
        path = case / "raw" / f"{src}.parquet"
        if not path.exists() or pq.read_metadata(path).num_rows == 0:
            continue
        f = pd.read_parquet(path)
        us = lambda base: num(f[f"common_{base}_us"] if f"common_{base}_us" in f.columns else f[f"common.{base}"])
        col = lambda name: num(f[name]) if name in f.columns else pd.Series(np.nan, index=f.index)
        if src == "adsbx":
            kind = col("type").map(ADSBX_TYPE).fillna("other")
        elif src == "planefinder":
            kind = col("data_source").map(PF_SOURCE).fillna("unknown")
        elif src == "tfms_ti":
            kind = "radar_grid"
        else:
            kind = "adsb"
        parts.append(pd.DataFrame(dict(
            case=case.name.split("-")[0], src=src, kind=kind,
            hex=f["common.adshex"].fillna(""), cs=f["common.callsign"].fillna("").str.strip(), tid=f["common.track_identifier"].fillna(""),
            t=us("position_timestamp") / 1e6, r=us("asi_received_timestamp") / 1e6,
            lat=col("common.latitude"), lon=col("common.longitude"), alt=col("common.altitude_ft"),
            nacp=col({"adsbx": "nac_p", "uavionix": "quality_indicators.nacp"}.get(src, "none")),
            nic=col({"adsbx": "nic", "uavionix": "quality_indicators.nucp_or_nic"}.get(src, "none")),
            sil=col({"adsbx": "sil", "uavionix": "quality_indicators.sil"}.get(src, "none")),
            nacv=col({"adsbx": "nac_v", "uavionix": "quality_indicators.nucr_or_nacv"}.get(src, "none")),
            alt_geom=col("alt_geom"), alt_baro=col("alt_baro"), rssi=col("rssi"), version=col("version"),
            station=f["station_id"].fillna("") if "station_id" in f.columns else "",
        )))
    d = pd.concat(parts, ignore_index=True).dropna(subset=["t", "lat", "lon"])
    d["late"] = d.r - d.t
    return d.sort_values("t").reset_index(drop=True)


def enu(lat0, lon0, lat, lon):
    """Metres east and north of a reference point; flat earth, fine within a few km."""
    return (lon - lon0) * 111320 * np.cos(np.radians(lat0)), (lat - lat0) * 110540


def against_reference(d: pd.DataFrame, ref_src: str, key: str = "hex", ref_kind: str = "adsb") -> pd.DataFrame:
    """For every plot of the other sources: where the reference put the same aircraft at that moment,
    split into metres along the flight direction and across it, plus the altitude difference.
    Aircraft are matched on `key` (hex, or callsign for TFMS which has no hex)."""
    rows = []
    ref_all = d[(d.src == ref_src) & (d.kind == ref_kind) & (d[key] != "")]
    others = d[(d.src != ref_src) & (d[key] != "")]
    for k_, ref in ref_all.groupby(key):
        ref = ref.sort_values("t").drop_duplicates("t")
        if len(ref) < 3:
            continue
        rt, rlat, rlon, ralt = ref.t.to_numpy(), ref.lat.to_numpy(), ref.lon.to_numpy(), ref.alt.to_numpy()
        for (src, kind), g in others[others[key] == k_].groupby(["src", "kind"]):
            t = g.t.to_numpy(); i = np.searchsorted(rt, t)
            ok = (i > 0) & (i < len(rt)); i = np.clip(i, 1, len(rt) - 1); a, b = i - 1, i
            gap = rt[b] - rt[a]; ok &= gap <= MAX_GAP_S
            if not ok.any():
                continue
            w = np.where(gap > 0, (t - rt[a]) / np.where(gap > 0, gap, 1), 0)
            lat_i = rlat[a] + w * (rlat[b] - rlat[a]); lon_i = rlon[a] + w * (rlon[b] - rlon[a]); alt_i = ralt[a] + w * (ralt[b] - ralt[a])
            ex, ny = enu(rlat[a], rlon[a], rlat[b], rlon[b]); dist = np.hypot(ex, ny); speed = dist / np.where(gap > 0, gap, 1)
            ux, uy = ex / np.where(dist > 0, dist, 1), ny / np.where(dist > 0, dist, 1)
            px, py = enu(lat_i, lon_i, g.lat.to_numpy(), g.lon.to_numpy())
            along = px * ux + py * uy; cross = -px * uy + py * ux
            ok &= speed > CROSS_MIN_SPEED
            rows.append(pd.DataFrame(dict(case=g.case.to_numpy(), src=src, kind=kind, key=k_, t=t, along=along, cross=cross, dist=np.hypot(px, py), speed=speed,
                                          dt=np.where(speed > MIN_SPEED, along / np.where(speed > 0, speed, 1), np.nan),
                                          dalt=g.alt.to_numpy() - alt_i, nacp=g.nacp.to_numpy(), station=g.station.to_numpy(), late=g.late.to_numpy()))[ok])
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    out["ref"] = ref_src
    return out


def self_scatter(d: pd.DataFrame, window: int = 9, max_span_s: float = 12.0, max_turn_deg: float = 3.0) -> pd.DataFrame:
    """Scatter of a source around a straight line through its own plots on straight legs.
    Windows of `window` plots spanning at most `max_span_s`; a window counts as straight when the
    direction of its first and second half differ by less than `max_turn_deg`."""
    rows = []
    def fit(ts, xs):
        A = np.vstack([ts - ts[0], np.ones(len(ts))]).T
        c = np.linalg.lstsq(A, xs, rcond=None)[0]
        return c[0], A @ c
    for (case, src, kind, hex_), g in d[d.hex != ""].groupby(["case", "src", "kind", "hex"]):
        g = g.sort_values("t").drop_duplicates("t")
        if len(g) < window:
            continue
        t, lat, lon, nacp = g.t.to_numpy(), g.lat.to_numpy(), g.lon.to_numpy(), g.nacp.to_numpy()
        for i in range(0, len(g) - window + 1, window // 2):
            tt = t[i:i + window]
            if not (1.0 <= tt[-1] - tt[0] <= max_span_s):
                continue
            x, y = enu(lat[i], lon[i], lat[i:i + window], lon[i:i + window])
            vx, fx = fit(tt, x); vy, fy = fit(tt, y); speed = np.hypot(vx, vy)
            if speed < MIN_SPEED:
                continue
            h = window // 2
            h1 = np.degrees(np.arctan2(fit(tt[:h], x[:h])[0], fit(tt[:h], y[:h])[0])); h2 = np.degrees(np.arctan2(fit(tt[h:], x[h:])[0], fit(tt[h:], y[h:])[0]))
            if abs((h1 - h2 + 180) % 360 - 180) > max_turn_deg:
                continue
            ux, uy = vx / speed, vy / speed
            cross = -(x - fx) * uy + (y - fy) * ux; along = (x - fx) * ux + (y - fy) * uy
            rows.append(pd.DataFrame(dict(case=case, src=src, kind=kind, hex=hex_, cross=cross, along=along, nacp=nacp[i:i + window], speed=speed)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def q(s, p):
    s = pd.Series(s).dropna()
    return float(np.percentile(s, p)) if len(s) else float("nan")


def summarise(v) -> dict:
    v = pd.Series(v).dropna()
    return dict(n=int(len(v)), p50=q(v, 50), p10=q(v, 10), p90=q(v, 90), spread=(q(v, 84) - q(v, 16)) / 2 if len(v) > 20 else float("nan"), abs_p50=q(v.abs(), 50), abs_p90=q(v.abs(), 90), abs_p99=q(v.abs(), 99))


def by(frame, keys, col):
    return {("|".join(map(str, k)) if isinstance(k, tuple) else str(k)): summarise(g[col]) for k, g in frame.groupby(keys) if len(g) >= 20}


def charts(d, ref, ref2, ss, out):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.facecolor": "white", "axes.grid": True, "grid.alpha": .3, "font.size": 9})
    lab = {"adsbx": "ADS-B Exchange", "uavionix": "uAvionix", "planefinder": "PlaneFinder", "tfms_ti": "TFMS TI"}

    # 1. offsets against uAvionix
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for src in ["adsbx", "planefinder"]:
        g = ref[(ref.src == src) & (ref.kind == "adsb")]
        ax[0].hist(g.cross.clip(-15, 15), bins=120, histtype="step", label=lab[src], density=True)
        ax[1].hist(g.along.clip(-300, 300), bins=120, histtype="step", label=lab[src], density=True)
        ax[2].hist(g.dt.clip(-1.5, 1.5), bins=120, histtype="step", label=lab[src], density=True)
    ax[0].set_title("across the flight direction (m)"); ax[1].set_title("along the flight direction (m)"); ax[2].set_title("time offset = along / speed (s)")
    for a in ax: a.legend(); a.axvline(0, color="k", lw=.6)
    fig.suptitle("ADS-B plots of other sources compared with where uAvionix put the aircraft at that exact time (Paris + Vancouver)")
    fig.tight_layout(); fig.savefig(out / "vs_uavionix.png", dpi=130); plt.close(fig)

    # 2. self scatter along vs across
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for a, src in zip(ax, ["uavionix", "adsbx", "planefinder"]):
        g = ss[(ss.src == src) & (ss.kind == "adsb")]
        a.scatter(g.along.clip(-150, 150), g.cross.clip(-15, 15), s=1, alpha=.15)
        a.set_xlim(-150, 150); a.set_ylim(-15, 15); a.set_title(f"{lab[src]}  (n={len(g):,})"); a.set_xlabel("along the line (m)"); a.set_ylabel("across the line (m)")
    fig.suptitle("Each source against a straight line through 9 of its own plots (straight legs only). Note the axes: across is 10x zoomed in")
    fig.tight_layout(); fig.savefig(out / "self_scatter.png", dpi=130); plt.close(fig)

    # 3. lateness curves per source and kind
    fig, ax = plt.subplots(figsize=(8, 4))
    for (src, kind), g in d.groupby(["src", "kind"]):
        if len(g) < 300:
            continue
        v = np.sort(g.late.clip(0, 60)); ax.plot(v, np.arange(len(v)) / len(v), label=f"{lab[src]} {kind} (n={len(g):,})")
    ax.set_xscale("log"); ax.set_xlim(0.1, 60); ax.set_xlabel("seconds between the position time and when ASI received the plot (log)"); ax.set_ylabel("share of plots received by then"); ax.legend(fontsize=8)
    ax.set_title("Lateness: how long after the aircraft was at a position we received the plot")
    fig.tight_layout(); fig.savefig(out / "lateness.png", dpi=130); plt.close(fig)

    # 4. NACp share per case
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
    for a, src in zip(ax, ["adsbx", "uavionix"]):
        g = d[(d.src == src)]
        tab = pd.crosstab(g.case, g.nacp.fillna(-1).astype(int), normalize="index") * 100
        tab.plot.bar(ax=a, stacked=True, width=.7, colormap="viridis", legend=False); a.set_ylabel("% of plots"); a.set_title(f"NACp of {lab[src]} plots per case (-1 = not present)")
        a.legend(title="NACp", fontsize=7, ncol=6, loc="lower center"); a.tick_params(axis="x", rotation=0)
    fig.tight_layout(); fig.savefig(out / "nacp_by_case.png", dpi=130); plt.close(fig)

    # 5. MLAT and TFMS
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    mm = against_reference(d, "adsbx", ref_kind="mlat"); mm = mm[(mm.kind == "mlat") & (mm.src == "planefinder")]
    ax[0].hist(mm.dist.clip(0, 5000), bins=100, histtype="step", label=f"PlaneFinder MLAT vs ADS-B Exchange MLAT, same aircraft (n={len(mm):,})", density=True)
    ms = self_scatter(d[(d.src == "adsbx") & (d.kind == "mlat")], window=7, max_span_s=40, max_turn_deg=5)
    ax[0].hist(ms.cross.abs().clip(0, 5000), bins=100, histtype="step", label=f"ADS-B Exchange MLAT, across its own straight line (n={len(ms):,})", density=True)
    ax[0].set_xscale("log"); ax[0].set_xlim(1, 5000); ax[0].set_title("MLAT positions: metres (log)"); ax[0].legend(fontsize=7)
    g = ref2[ref2.src == "tfms_ti"]
    ax[1].hist(g.cross.clip(-3000, 3000), bins=100, histtype="step", label="across"); ax[1].hist(g.along.clip(-3000, 3000), bins=100, histtype="step", label="along")
    ax[1].set_title(f"TFMS TI vs ADS-B Exchange, same callsign (m, n={len(g):,})"); ax[1].legend()
    ax[2].hist(g.dalt.clip(-3000, 3000), bins=100, histtype="step"); ax[2].set_title("TFMS TI altitude minus ADS-B altitude (ft)")
    fig.tight_layout(); fig.savefig(out / "mlat_tfms.png", dpi=130); plt.close(fig)

    # 6. PlaneFinder stations: time offset and lateness
    pf = ref[(ref.src == "planefinder") & (ref.kind == "adsb") & (ref.station != "")]
    st = pf.groupby("station").agg(n=("dt", "size"), dt=("dt", "median"), late=("late", "median")).query("n >= 30").sort_values("dt")
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
    ax[0].bar(range(len(st)), st.dt); ax[0].set_xticks(range(len(st))); ax[0].set_xticklabels(st.index, rotation=90, fontsize=6); ax[0].set_ylabel("s"); ax[0].set_title("median time offset vs uAvionix per PlaneFinder receiver")
    ax[1].bar(range(len(st)), st.late); ax[1].set_xticks(range(len(st))); ax[1].set_xticklabels(st.index, rotation=90, fontsize=6); ax[1].set_ylabel("s"); ax[1].set_title("median lateness per PlaneFinder receiver")
    fig.tight_layout(); fig.savefig(out / "pf_stations.png", dpi=130); plt.close(fig)

    # 7. geometric minus barometric altitude per case
    fig, ax = plt.subplots(figsize=(8, 3.6))
    g = d[(d.src == "adsbx") & d.alt_geom.notna() & d.alt_baro.notna()]
    for case, gg in g.groupby("case"):
        ax.hist((gg.alt_geom - gg.alt_baro).clip(-1500, 3000), bins=90, histtype="step", label=case, density=True)
    ax.legend(); ax.set_xlabel("geometric (GPS) altitude minus barometric altitude, ft"); ax.set_title("GPS altitude minus barometric altitude, per case")
    fig.tight_layout(); fig.savefig(out / "alt_geom_baro.png", dpi=130); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="src/data/cases")
    ap.add_argument("--out", default=str(pathlib.Path.home() / "notes/track_quality_and_state_estimation/sources/source-accuracy"))
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cases = sorted(p for p in pathlib.Path(a.cases).iterdir() if (p / "case.json").exists())
    d = pd.concat([load(c) for c in cases], ignore_index=True)
    print(f"{len(d):,} raw plots from {len(cases)} cases")
    R = {}

    # coverage of the accuracy fields
    R["counts"] = {f"{c}|{s}|{k}": int(n) for (c, s, k), n in d.groupby(["case", "src", "kind"]).size().items()}
    for field in ["nacp", "nic", "sil", "nacv"]:
        R[f"{field}_share"] = {f"{c}|{s}": {int(k): int(v) for k, v in g[field].fillna(-1).value_counts().sort_index().items()} for (c, s), g in d.groupby(["case", "src"]) if g[field].notna().any()}
    ad = d[(d.src == "adsbx") & (d.kind == "adsb")]
    R["adsbx_nacp_x_nic"] = {int(k): {int(kk): int(vv) for kk, vv in g.nic.fillna(-1).value_counts().items()} for k, g in ad.groupby(ad.nacp.fillna(-1))}
    R["adsbx_nacp_by_version"] = {int(k): {int(kk): int(vv) for kk, vv in g.nacp.fillna(-1).value_counts().items()} for k, g in ad.groupby(ad.version.fillna(-1))}
    per = ad.dropna(subset=["nacp"]).groupby(["case", "hex"]).nacp.agg(["nunique", "min", "max", "count"])
    R["adsbx_nacp_per_aircraft"] = dict(aircraft=int(len(per)), distinct_values=per["nunique"].value_counts().to_dict(), range_ge_3=int((per["max"] - per["min"] >= 3).sum()),
                                        zero_aircraft=int((per["min"] == 0).sum()), zero_aircraft_also_good=int(((per["min"] == 0) & (per["max"] >= 8)).sum()))
    R["alt_geom_minus_baro_ft"] = by(ad.assign(dg=ad.alt_geom - ad.alt_baro).dropna(subset=["dg"]), ["case"], "dg")

    # 1. against uAvionix (Paris, Vancouver) and against ADS-B Exchange (all cases)
    ref = against_reference(d, "uavionix")
    ref2 = against_reference(d, "adsbx")
    tf = against_reference(d, "adsbx", key="cs"); tf = tf[tf.src == "tfms_ti"]
    ref2 = pd.concat([ref2[ref2.src != "tfms_ti"], tf], ignore_index=True)
    for name, frame in [("vs_uavionix", ref), ("vs_adsbx", ref2)]:
        R[name] = {}
        for col in ["cross", "along", "dt", "dalt", "dist"]:
            R[name][col] = by(frame, ["case", "src", "kind"], col)
        R[name]["all_cases"] = {col: by(frame, ["src", "kind"], col) for col in ["cross", "along", "dt", "dalt", "dist"]}
    R["vs_uavionix_by_nacp"] = by(ref[(ref.src == "adsbx") & (ref.kind == "adsb")].dropna(subset=["nacp"]), ["nacp"], "cross")
    pf = ref[(ref.src == "planefinder") & (ref.kind == "adsb") & (ref.station != "")]
    R["pf_stations"] = {st: dict(n=int(len(g)), dt_p50=q(g.dt, 50), dt_spread=summarise(g.dt)["spread"], late_p50=q(g.late, 50), late_p90=q(g.late, 90), cross_spread=summarise(g.cross)["spread"]) for st, g in pf.groupby("station") if len(g) >= 30}
    R["pf_dt_between_stations"] = summarise(pd.Series([v["dt_p50"] for v in R["pf_stations"].values()]))

    # 2. three cornered hat on the across track offsets, ADS-B plots only
    hat = {}
    for case in ref.case.unique():
        v = {}
        for s in ["adsbx", "planefinder"]:
            g = ref[(ref.case == case) & (ref.src == s) & (ref.kind == "adsb")].cross.dropna(); v[s] = float(np.var(g[g.abs() < 100])) if len(g) > 50 else np.nan
        g = ref2[(ref2.case == case) & (ref2.src == "planefinder") & (ref2.kind == "adsb")].cross.dropna(); vap = float(np.var(g[g.abs() < 100])) if len(g) > 50 else np.nan
        vau, vup = v["adsbx"], v["planefinder"]
        if not any(np.isnan([vau, vup, vap])):
            own = {"uavionix": (vau + vup - vap) / 2, "adsbx": (vau + vap - vup) / 2, "planefinder": (vup + vap - vau) / 2}
            hat[case] = {k: (float(np.sqrt(x)) if x > 0 else 0.0) for k, x in own.items()}
            hat[case]["pair_std"] = {"uavionix-adsbx": float(np.sqrt(vau)), "uavionix-planefinder": float(np.sqrt(vup)), "adsbx-planefinder": float(np.sqrt(vap))}
    R["three_cornered_hat"] = hat

    # 3. self scatter
    ss = self_scatter(d)
    R["self_scatter"] = {col: by(ss, ["src", "kind"], col) for col in ["cross", "along"]}
    R["self_scatter_by_case"] = {col: by(ss, ["case", "src", "kind"], col) for col in ["cross", "along"]}
    R["self_scatter_by_nacp"] = by(ss[ss.kind == "adsb"].dropna(subset=["nacp"]), ["src", "nacp"], "cross")

    # 4. lateness
    R["lateness"] = {k: dict(n=int(len(g)), p50=q(g.late, 50), p90=q(g.late, 90), p99=q(g.late, 99), max=float(g.late.max()), over_10s=int((g.late > 10).sum()), over_60s=int((g.late > 60).sum()))
                     for k, g in {**{"|".join(k): g for k, g in d.groupby(["src", "kind"])}, **{"|".join(k): g for k, g in d.groupby(["case", "src", "kind"])}}.items() if len(g) >= 20}
    # plots that arrive out of order within one source track
    oo = d.sort_values("r").groupby(["src", "tid"]).t.diff() < 0
    R["out_of_order"] = {"|".join(k): dict(n=int(len(g)), out_of_order=int(oo[g.index].sum())) for k, g in d.groupby(["src", "kind"]) if len(g) >= 20}

    (out / "source_accuracy.json").write_text(json.dumps(R, indent=1, default=float))
    ref.to_parquet(out / "vs_uavionix.parquet", index=False); ref2.to_parquet(out / "vs_adsbx.parquet", index=False); ss.to_parquet(out / "self_scatter.parquet", index=False)
    charts(d, ref, ref2, ss, out)
    print("written to", out)


if __name__ == "__main__":
    main()
