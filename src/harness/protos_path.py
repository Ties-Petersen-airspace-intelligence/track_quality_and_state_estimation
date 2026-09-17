"""Put the generated protobuf modules on sys.path. Import this before any *_pb2 import."""
import pathlib, sys

GENERATED = pathlib.Path(__file__).parent / "generated"
if str(GENERATED) not in sys.path:
    sys.path.insert(0, str(GENERATED))
