"""Candidate sets: which fusion tables and kinds of error a run looks at, and where its files go."""
import pathlib

# how many candidates of each kind to draw after checking, so one kind cannot fill the list
SETS = {
    # the first run: both fusions, every kind
    "": dict(fusions=("append", "regular"),
             quota={"position spike": 45, "teleport": 30, "flip-flop": 25, "sharp turn": 20,
                    "altitude jump": 25, "speed jump": 20, "uAvionix altitude": 4, "uAvionix speed": 4}),
    # what Flyways shows: regular fusion, spikes that go out and come back
    "regular_spikes": dict(fusions=("regular",), quota={"position spike": 100, "altitude spike": 50}),
}


def path(out: pathlib.Path, stem: str, name: str, suffix: str = ".parquet") -> pathlib.Path:
    """out/<day>/<stem>.parquet for the first run, out/<day>/<stem>_<set>.parquet for the others."""
    return out / (f"{stem}_{name}{suffix}" if name else f"{stem}{suffix}")
