"""Compile the proto snapshot in src/harness/protos into Python modules in src/harness/generated.

usage: uv run src/harness/build_protos.py
"""
import pathlib, sys

from grpc_tools import protoc

HERE = pathlib.Path(__file__).parent
PROTOS = HERE / "protos"
OUT = HERE / "generated"


def main():
    OUT.mkdir(exist_ok=True)
    files = sorted(str(p.relative_to(PROTOS)) for p in PROTOS.rglob("*.proto"))
    # the well known types (google/protobuf/*.proto) ship inside grpc_tools
    import grpc_tools
    include_google = str(pathlib.Path(grpc_tools.__file__).parent / "_proto")
    code = protoc.main(["protoc", f"-I{PROTOS}", f"-I{include_google}", f"--python_out={OUT}", f"--pyi_out={OUT}"] + files)
    if code != 0:
        sys.exit(f"protoc failed with code {code}")

    # every generated folder needs to be a package, and the imports inside the generated code are absolute
    # (for example `from uni_track_plot_schema.proto import plot_pb2`), so src/harness/generated goes on sys.path
    for folder in {p.parent for p in OUT.rglob("*_pb2.py")} | {OUT}:
        for d in [folder] + list(folder.relative_to(OUT).parents if folder != OUT else []):
            init = (OUT / d if d != pathlib.Path(".") else OUT) / "__init__.py"
            init.touch()
    print(f"compiled {len(files)} proto files into {OUT}")


if __name__ == "__main__":
    main()
