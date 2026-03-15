"""Amazon Timestream アクセス層"""

from __future__ import annotations

import os
from typing import Any

import boto3

_region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")

# Timestream は endpoint_url が必要
_write_client = boto3.client("timestream-write", region_name=_region)
_query_client = boto3.client("timestream-query", region_name=_region)

_DB = lambda: os.environ["TIMESTREAM_DATABASE"]  # noqa: E731
_TABLE = lambda: os.environ["TIMESTREAM_TABLE"]  # noqa: E731


def write_telemetry(record: dict[str, Any]) -> None:
    """テレメトリを Timestream に書き込む"""
    robot_id = record["robot_id"]
    timestamp_ms = str(int(_iso_to_epoch_ms(record["timestamp"])))

    dimensions = [
        {"Name": "robot_id", "Value": robot_id},
        {"Name": "status", "Value": record.get("status", "UNKNOWN")},
        {"Name": "room", "Value": record.get("position", {}).get("room", "unknown")},
    ]

    measures = [
        {
            "MeasureName": "battery_level",
            "MeasureValue": str(record["battery_level"]),
            "MeasureValueType": "DOUBLE",
        },
        {
            "MeasureName": "speed",
            "MeasureValue": str(record["speed"]),
            "MeasureValueType": "DOUBLE",
        },
        {
            "MeasureName": "position_x",
            "MeasureValue": str(record.get("position", {}).get("x", 0)),
            "MeasureValueType": "DOUBLE",
        },
        {
            "MeasureName": "position_y",
            "MeasureValue": str(record.get("position", {}).get("y", 0)),
            "MeasureValueType": "DOUBLE",
        },
    ]

    records = [
        {
            "Dimensions": dimensions,
            "MeasureName": m["MeasureName"],
            "MeasureValue": m["MeasureValue"],
            "MeasureValueType": m["MeasureValueType"],
            "Time": timestamp_ms,
            "TimeUnit": "MILLISECONDS",
        }
        for m in measures
    ]

    _write_client.write_records(
        DatabaseName=_DB(),
        TableName=_TABLE(),
        Records=records,
        CommonAttributes={},
    )


def query_telemetry(robot_id: str, minutes: int = 60) -> list[dict[str, Any]]:
    """過去 N 分間のテレメトリを取得"""
    query = f"""
        SELECT time, measure_name, measure_value::double
        FROM "{_DB()}"."{_TABLE()}"
        WHERE robot_id = '{robot_id}'
          AND measure_name IN ('battery_level', 'speed')
          AND time >= ago({minutes}m)
        ORDER BY time ASC
    """
    resp = _query_client.query(QueryString=query)
    return _parse_timestream_result(resp)


def _parse_timestream_result(resp: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [c["Name"] for c in resp["ColumnInfo"]]
    rows = []
    for row in resp.get("Rows", []):
        values = [d.get("ScalarValue") for d in row["Data"]]
        rows.append(dict(zip(columns, values, strict=False)))
    return rows


def _iso_to_epoch_ms(iso: str) -> float:
    from datetime import datetime

    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.timestamp() * 1000
