"""Load a case folder into raw plot protos, in the order we received them.

Each source table in BigQuery is a flattening of that source's plot proto: nested messages
become dotted column names (common.latitude), repeated fields become arrays. So a row can be
turned back into the proto by walking the message descriptor and picking the matching columns.
"""
from __future__ import annotations

import json, math, pathlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from google.protobuf.descriptor import FieldDescriptor as FD
from google.protobuf.message import Message

from . import protos_path  # noqa: F401  (sys.path side effect)
from uni_track_source_adsbx_plot_schema.proto import plot_pb2 as adsbx_pb2
from uni_track_source_asa_plot_schema.proto import plot_pb2 as asa_pb2
from uni_track_source_planefinder_plot_schema.proto import plot_pb2 as planefinder_pb2
from uni_track_source_stdds_plot_schema.proto import position_report_pb2 as stdds_pb2
from uni_track_source_tfms_plot_schema.proto import tfms_or_pb2, tfms_ti_pb2
from uni_track_source_ual_plot_schema.proto import plot_pb2 as ual_pb2
from uni_track_source_uavionix_plot_schema.proto import flight_line_pb2 as uavionix_pb2

# source name -> the proto class its table rows turn into
SOURCE_MESSAGE = {
    "adsbx": adsbx_pb2.ADSBXPlot,
    "planefinder": planefinder_pb2.PlanefinderPlot,
    "uavionix": uavionix_pb2.AsterixCat021,
    "stdds": stdds_pb2.PositionReport,
    "tfms_ti": tfms_ti_pb2.TFMSTrackInformationPlot,
    "tfms_or": tfms_or_pb2.TFMSOceanicReportPlot,
    "ual": ual_pb2.UalPlot,
    "asa": asa_pb2.AsaPlot,
}


@dataclass
class RawPlot:
    source: str            # table name, e.g. "adsbx"
    row: int               # row number in raw/<source>.parquet; source and row name one raw plot
    received_us: int       # when it reached us, common.asi_received_timestamp
    position_us: int       # common.position_timestamp
    proto: Message         # the source's plot message, common inside


def load_case(folder: str | pathlib.Path) -> list[RawPlot]:
    """All raw plots of a case, sorted by the time we received them."""
    folder = pathlib.Path(folder)
    plots: list[RawPlot] = []
    for source, message_class in SOURCE_MESSAGE.items():
        path = folder / "raw" / f"{source}.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        if frame.empty:
            continue
        columns = set(frame.columns)
        for number, row in enumerate(frame.to_dict("records")):
            message = message_class()
            fill_message(message, row, columns, "")
            plots.append(RawPlot(source, number, message.common.asi_received_timestamp, message.common.position_timestamp, message))
    plots.sort(key=lambda p: (p.received_us, p.position_us))
    return plots


def fill_message(message: Message, row: dict, columns: set[str], prefix: str) -> None:
    """Copy the row's values into the message, one descriptor field at a time."""
    for field in message.DESCRIPTOR.fields:
        column = prefix + field.name

        if field.type == FD.TYPE_MESSAGE and not field.is_repeated:
            if any(c.startswith(column + ".") for c in columns):
                child = getattr(message, field.name)
                fill_message(child, row, columns, column + ".")
                # a nested message with nothing filled in stays unset
                if not child.ListFields() and field.has_presence:
                    message.ClearField(field.name)
            continue

        value = pick(row, columns, column, field)
        if value is None:
            continue
        if field.is_repeated:
            getattr(message, field.name).extend(scalar(v, field) for v in value if not missing(v))
        else:
            setattr(message, field.name, scalar(value, field))


def pick(row: dict, columns: set[str], column: str, field) -> object:
    """The row value for a field. Timestamps use the exact microsecond twin column when there is one."""
    exact = column.replace(".", "_") + "_us"
    if field.type == FD.TYPE_INT64 and exact in columns and not missing(row.get(exact)):
        return row[exact]
    value = row.get(column)
    return None if missing(value) else value


def missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, (list, np.ndarray)):
        return len(value) == 0
    return pd.isna(value) if not isinstance(value, (str, bytes)) else False


def scalar(value, field):
    """bq JSON export gives every scalar as a string; cast to what the proto field wants."""
    if field.type in (FD.TYPE_INT64, FD.TYPE_INT32, FD.TYPE_UINT32, FD.TYPE_UINT64, FD.TYPE_SINT32, FD.TYPE_SINT64):
        return int(float(value))
    if field.type in (FD.TYPE_FLOAT, FD.TYPE_DOUBLE):
        return float(value)
    if field.type == FD.TYPE_BOOL:
        return value if isinstance(value, bool) else str(value).lower() == "true"
    if field.type == FD.TYPE_ENUM:
        text = str(value)
        if text.lstrip("-").isdigit():
            return int(text)
        return field.enum_type.values_by_name[text].number
    if field.type == FD.TYPE_BYTES:
        return value if isinstance(value, bytes) else str(value).encode()
    return str(value)


def case_info(folder: str | pathlib.Path) -> dict:
    return json.loads((pathlib.Path(folder) / "case.json").read_text())
