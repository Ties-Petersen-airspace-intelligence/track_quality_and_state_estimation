"""The comment written next to every proto field, by dotted field path, for the viewer's field list.

The compiled Python modules carry no comments, so the proto snapshot is compiled once more into a descriptor set
with source info, and the comments are read from there.
"""
from __future__ import annotations

import pathlib, tempfile
from functools import cache

import grpc_tools
from google.protobuf import descriptor_pb2
from grpc_tools import protoc

PROTOS = pathlib.Path(__file__).parent / "protos"


@cache
def messages() -> dict[str, dict[str, tuple[str, str]]]:
    """Every message by full name: field name -> (comment, full name of the field's message type or ""). The comment at the end
    of a field's line wins over the one above it, which is often a heading for several fields."""
    files = sorted(str(p.relative_to(PROTOS)) for p in PROTOS.rglob("*.proto"))
    include_google = str(pathlib.Path(grpc_tools.__file__).parent / "_proto")
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "set.pb"
        if protoc.main(["protoc", f"-I{PROTOS}", f"-I{include_google}", "--include_source_info", f"--descriptor_set_out={out}"] + files) != 0:
            return {}
        descriptors = descriptor_pb2.FileDescriptorSet.FromString(out.read_bytes())
    found = {}
    for file in descriptors.file:
        comments = {tuple(loc.path): (loc.trailing_comments or loc.leading_comments).strip() for loc in file.source_code_info.location}
        package = "." + file.package if file.package else ""
        for i, message in enumerate(file.message_type):
            walk(message, package, (4, i), comments, found)
    return found


def walk(message, prefix: str, path: tuple, comments: dict, found: dict) -> None:
    """Record a message's fields, then its nested messages; path is the message's place in the file (source info path)."""
    name = f"{prefix}.{message.name}"
    found[name.lstrip(".")] = {field.name: (" ".join(comments.get(path + (2, k), "").split()), field.type_name.lstrip("."))
                              for k, field in enumerate(message.field)}
    for j, nested in enumerate(message.nested_type):
        walk(nested, name, path + (3, j), comments, found)


def flat(root: str, prefix: str = "") -> dict[str, str]:
    """A message's comments by dotted path, nested messages flattened, as the tables name their columns."""
    out = {}
    for field, (comment, type_name) in messages().get(root, {}).items():
        if type_name in messages():
            out.update(flat(type_name, prefix + field + "."))
        out[prefix + field] = comment
    return out
