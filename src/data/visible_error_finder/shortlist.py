"""Step 6: merge the picture ratings with the candidates and write the shortlist for the review page.

usage: uv run data/visible_error_finder/shortlist.py --ratings <folder with ratings_*.json> [--size 55] [--set regular_spikes]

The ratings come from looking at every picture (visible and clean, 0 to 3 each, plus a title and a
plain sentence of what you see). Writes out/shortlist.json, or out/<set>.json for a named set. Run from src/.
"""
import argparse, json, pathlib

import pandas as pd

from sets import SETS, path

HERE = pathlib.Path(__file__).parent
DAYS = ("2026-09-21", "2026-09-22")
MOST_PER_KIND = {"uAvionix altitude": 3, "uAvionix speed": 3, "position spike": 32, "altitude spike": 16}
MOST_PER_KIND_DEFAULT = 14


def card(r, name: str = "") -> dict:
    """What the review page shows for one candidate."""
    return dict(id=r.id, day=r.day, kind=r.kind, fusion=getattr(r, "seen_in", "regular"), who=r.who, title=r.title,
                what_you_see=r.what_you_see, summary=r.summary, visible=int(r.visible), clean=int(r.clean),
                speed_kt=None if pd.isna(r.gs) else round(float(r.gs)), regular_plots=int(r.regular_plots),
                over_us=bool(-170 <= r.lon <= -50 and 15 <= r.lat <= 72), callsign=None if pd.isna(r.cs) else r.cs,
                t_event=float(r.t_event), lat=float(r.lat), lon=float(r.lon),
                plat=None if pd.isna(r.plat) else float(r.plat), plon=None if pd.isna(r.plon) else float(r.plon), tid=r.tid, hex=r.hex,
                picture=f"out/{r.day}/{path(pathlib.Path(''), 'pictures', name, '')}/{r.id}.png", set=name)


def rated_candidates(ratings_folder: str, name: str = "") -> pd.DataFrame:
    """Candidates of every day, with the ratings of their pictures and their regular fusion plot count."""
    candidates = pd.concat([pd.read_parquet(path(HERE / "out" / day, "checked", name)).assign(day=day) for day in DAYS])
    ratings = pd.DataFrame([r for f in sorted(pathlib.Path(ratings_folder).glob("ratings_*.json")) for r in json.loads(f.read_text())])
    rated = candidates.merge(ratings.rename(columns={"fusion": "seen_in"}), on="id")
    # since 22 Sep regular was still filling, some have none
    regular = pd.concat([pd.read_parquet(path(HERE / "out" / day, "plots", name), columns=["id", "fusion"]) for day in DAYS])
    rated["regular_plots"] = rated.id.map(regular[regular.fusion == "regular"].groupby("id").size()).fillna(0).astype(int)
    return rated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ratings", required=True)
    parser.add_argument("--size", type=int, default=55)
    parser.add_argument("--set", default="", choices=SETS)
    args = parser.parse_args()

    rated = rated_candidates(args.ratings, args.set)

    # clearly visible and clean first, then the finder's own score
    rated = rated[(rated.visible >= 2) & (rated.clean >= 1)]
    # spikes that come back to the path worked in Flyways, teleports did not
    if "returns" in rated:
        rated = rated[rated.returns.astype(bool)]
    rated = rated.sort_values(["visible", "clean", "score"], ascending=False)

    # one per aircraft, a limit per kind so the list stays varied
    rated = rated[~rated.hex.fillna(rated.tid).duplicated()]
    rated = pd.concat([group.head(MOST_PER_KIND.get(kind, MOST_PER_KIND_DEFAULT)) for kind, group in rated.groupby("kind", sort=False)])
    rated = rated.sort_values(["visible", "clean", "score"], ascending=False).head(args.size)

    shortlist = [card(r, args.set) for r in rated.itertuples()]
    (HERE / "out" / f"{args.set or 'shortlist'}.json").write_text(json.dumps(shortlist, indent=1))
    print(f"{len(shortlist)} on the shortlist")
    print(rated.kind.value_counts().to_string())


if __name__ == "__main__":
    main()
