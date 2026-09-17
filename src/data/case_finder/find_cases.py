"""Scan one UTC day of fused output for moments that look wrong and turn them into review cases.

usage: python find_cases.py --day 2026-09-16 [--dry-run] [--per-rule 10]

Writes out/<day>/hits.json (every hit BigQuery returned) and out/<day>/cases.json
(merged, capped, with a plain-language reason per case). Marks from an earlier
cases.json for the same day are kept.
"""
import argparse, datetime, json, pathlib

import bq

HERE = pathlib.Path(__file__).parent
SOURCE_NAME = {1: "TFMS TI", 2: "TFMS OR", 3: "PlaneFinder", 4: "ADS-B Exchange", 5: "Alaska ACARS", 6: "United",
               7: "Spire", 8: "UDL", 9: "MEIS", 10: "STDDS", 11: "uAvionix", 12: "FAA ADS-B EDP", 13: "Aireon"}
MARGIN_DEG = 0.3          # box half-width around the hit
MARGIN_S = 600            # time either side of the hit
MERGE_DEG = 0.3           # hits closer than this in space ...
MERGE_S = 600             # ... and time are the same case
FAR_END_MAX_DEG = 3.0     # include the other end of a hit in the box if it is closer than this

RULE_TITLE = {
    "jump": "Impossible jump",
    "recorrelation": "Hex moved to another track",
    "rewritten_past": "Past rewritten by regular fusion",
    "altitude_spike": "Altitude spike",
    "gap_reappear": "Gap, then reappeared too far away",
    "source_zigzag": "Sources disagree, track zigzags",
}


def src(n):
    return SOURCE_NAME.get(int(n), str(n)) if n not in (None, "") else "unknown"


def hms(us):
    return datetime.datetime.fromtimestamp(int(us) / 1e6, datetime.timezone.utc).strftime("%H:%M:%S")


def f(v, nd=0):
    return None if v in (None, "") else round(float(v), nd)


def reason(h):
    """Plain words for why this hit was picked."""
    who = h["cs"] or h["hex"] or h["tid"]
    r = h["rule"]
    if r == "jump":
        on_ground = (f(h["alt"]) or 0) <= 100 and (f(h["palt"]) or 0) <= 100 and (f(h["gs"]) or 0) < 5 and (f(h["pgs"]) or 0) < 5
        same_lat = h.get("plat") not in (None, "") and abs(float(h["lat"]) - float(h["plat"])) < 0.01 and abs(float(h["lon"]) - float(h["plon"])) > 0.1
        text = (f"Track {who} moved {f(h['dist_m'])/1000:.1f} km in {f(h['dt_s'],1)} s between two consecutive fused plots, "
                f"which is {f(h['metric']):,} kt. No aircraft flies that fast. The earlier plot came from {src(h['psrc'])}, this one from {src(h['src'])}.")
        if on_ground:
            text += (" Both plots say altitude 0 and speed 0, so this is something standing on the ground, a vehicle or a parked aircraft, "
                     "and the two sources put it in two different places.")
        if same_lat:
            text += (" The two positions share the same latitude and differ only in longitude. That is the signature of an ADS-B position decoding error: "
                     "a receiver decoded the compact position message into the wrong longitude zone.")
        if not on_ground and not same_lat:
            text += " Either two aircraft were glued into one track, or one source gave a wrong position."
        return text
    if r == "altitude_spike":
        return (f"Track {who} went from {f(h['palt'])} ft to {f(h['alt'])} ft in {f(h['dt_s'],1)} s, about {f(float(h['metric']) / float(h['dt_s']) * 60)} ft per minute. "
                f"Real climbs and descents stay well under 10,000 ft per minute. Previous plot from {src(h['psrc'])}, this one from {src(h['src'])}.")
    if r == "gap_reappear":
        return (f"Track {who} had no fused plot for {f(h['dt_s'])/60:.1f} minutes, then reappeared {f(h['dist_m'])/1000:.0f} km away. "
                f"Covering that distance in that time means {f(h['metric'])} kt. Either the track was lost and picked up on a different aircraft, "
                f"or the aircraft flew unseen and the reappearance is genuine but the gap itself is a coverage problem.")
    if r == "source_zigzag":
        return (f"Three consecutive fused plots of track {who} within {f(h['dt_s'],1)} s: {src(h['psrc'])}, then {src(h['src'])}, then {src(h['psrc'])} again. "
                f"The middle plot sits {f(h['metric'])} m off the straight line between its neighbours. Two sources disagree on where the aircraft is "
                f"and fusion switches between them instead of smoothing.")
    if r == "recorrelation":
        far = f(h["dist_m"]) / 1000
        other = f"{float(h['plat']):.2f} N, {float(h['plon']):.2f} E" if h.get("plat") not in (None, "") else "an unknown position"
        if float(h["dt_s"]) < 30 and far > 50:
            return (f"Hex {h['hex']} is in two places at once. Track {h['n']} reported it at {other}, and {f(h['dt_s'],1)} s later track {h['tid']} "
                    f"reported it here, {far:.0f} km away. Two fused tracks carry the same hex at the same time, so at least one of them has the wrong aircraft. "
                    f"The other end is outside this box; the dashed line on the map points to it. Callsign at that moment: {h['cs'] or 'none'}.")
        return (f"Hex {h['hex']} was on track {h['n']} and {f(h['dt_s'],1)} s later appears on track {h['tid']}, {far:.1f} km from its last plot at {other}. "
                f"The current system changed its mind about which aircraft these reports belong to. Callsign at that moment: {h['cs'] or 'none'}.")
    if r == "rewritten_past":
        return (f"In one ten minute block, {h['n']} fused plots of track {who} were later replaced by regular fusion, the oldest one "
                f"{f(h['dt_s'])/60:.0f} minutes after its own position time. Append fusion first emitted something that regular fusion later decided was wrong.")
    return r


def merge(hits, per_rule):
    """Sort strongest first per rule, merge hits that are close in space and time, cap per rule."""
    cases, kept, per_tid = [], {r: 0 for r in RULE_TITLE}, {}
    for h in sorted(hits, key=lambda x: -float(x["metric"] or 0)):
        t = int(h["t_us"]) / 1e6
        home = None
        for c in cases:
            if abs(c["lat"] - float(h["lat"])) < MERGE_DEG and abs(c["lon"] - float(h["lon"])) < MERGE_DEG and abs(c["t"] - t) < MERGE_S:
                home = c
                break
        if home:
            home["hits"].append(h)
            continue
        if kept[h["rule"]] >= per_rule or per_tid.get((h["rule"], h["tid"]), 0) >= 2:
            continue
        kept[h["rule"]] += 1
        per_tid[(h["rule"], h["tid"])] = per_tid.get((h["rule"], h["tid"]), 0) + 1
        cases.append(dict(lat=float(h["lat"]), lon=float(h["lon"]), t=t, hits=[h]))
    return cases


def build_case(day, i, c):
    """i is only the position in the list; the id is built from the first hit so it stays the same across reruns."""
    h0 = c["hits"][0]
    ts = [int(h["t_us"]) / 1e6 for h in c["hits"]]
    lats = [float(h["lat"]) for h in c["hits"]]
    lons = [float(h["lon"]) for h in c["hits"]]
    # the other end of a hit belongs in the box too, unless it is very far away
    for h in c["hits"]:
        if h.get("plat") not in (None, "") and abs(float(h["plat"]) - lats[0]) < FAR_END_MAX_DEG and abs(float(h["plon"]) - lons[0]) < FAR_END_MAX_DEG:
            lats.append(float(h["plat"])); lons.append(float(h["plon"]))
    rules = sorted({h["rule"] for h in c["hits"]}, key=lambda r: list(RULE_TITLE).index(r))
    t0, t1 = min(ts) - MARGIN_S, max(ts) + MARGIN_S
    iso = lambda s: datetime.datetime.fromtimestamp(s, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    others = len(c["hits"]) - 1
    return dict(
        id=f"{h0['rule']}-{h0['tid']}-{hms(h0['t_us']).replace(':', '')}",
        day=day, rule=h0["rule"], rules=rules, title=RULE_TITLE[h0["rule"]],
        who=h0["cs"] or h0["hex"] or h0["tid"], tid=h0["tid"], hex=h0["hex"], callsign=h0["cs"],
        t_start=iso(t0), t_end=iso(t1),
        box=dict(lat_min=round(min(lats) - MARGIN_DEG, 3), lat_max=round(max(lats) + MARGIN_DEG, 3),
                 lon_min=round(min(lons) - MARGIN_DEG, 3), lon_max=round(max(lons) + MARGIN_DEG, 3)),
        reason=reason(h0) + (f" {others} other hit{'s' if others > 1 else ''} fall in the same area and time: " +
                             ", ".join(sorted({RULE_TITLE[h['rule']].lower() for h in c['hits'][1:]})) + "." if others else ""),
        rule_total_that_day=int(h0["rule_total"]),
        focus_tids=sorted({x for h in c["hits"] for x in (h["tid"], h["n"] if h["rule"] == "recorrelation" else None) if x}),
        focus_hexes=sorted({h["hex"] for h in c["hits"] if h["hex"]}),
        hits=[dict(rule=h["rule"], tid=h["tid"], prev_tid=h["n"] if h["rule"] == "recorrelation" else None, hex=h["hex"], callsign=h["cs"], time=hms(h["t_us"]), t_us=int(h["t_us"]),
                   lat=float(h["lat"]), lon=float(h["lon"]), metric=f(h["metric"], 1), source=src(h["src"]),
                   other_lat=f(h.get("plat"), 4), other_lon=f(h.get("plon"), 4)) for h in c["hits"]],
        mark=None, note="",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--per-rule", type=int, default=10)
    ap.add_argument("--from-hits", action="store_true", help="rebuild cases.json from the saved hits.json without querying")
    a = ap.parse_args()
    out = HERE / "out" / a.day
    out.mkdir(parents=True, exist_ok=True)
    sql = (HERE / "sql" / "detect.sql").read_text().replace("{day}", a.day)
    if a.dry_run:
        bq.report_cost("detect", sql)
        return
    if a.from_hits:
        hits = json.loads((out / "hits.json").read_text())
    else:
        hits = bq.run("detect", sql)
        (out / "hits.json").write_text(json.dumps(hits))
    totals = {}
    for h in hits:
        totals[h["rule"]] = int(h["rule_total"])
    print("hits per rule that day:", totals)
    old = {}
    if (out / "cases.json").exists():
        old = {c["id"]: c for c in json.loads((out / "cases.json").read_text())}
    cases = [build_case(a.day, i, c) for i, c in enumerate(merge(hits, a.per_rule))]
    for c in cases:
        if c["id"] in old:
            c["mark"], c["note"] = old[c["id"]]["mark"], old[c["id"]]["note"]
    (out / "cases.json").write_text(json.dumps(cases, indent=1))
    print(f"{len(cases)} cases written to {out / 'cases.json'}")


if __name__ == "__main__":
    main()
