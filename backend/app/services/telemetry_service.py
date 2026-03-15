"""DynamoDB ベースのテレメトリ履歴サービス"""

from __future__ import annotations

import os
import time
from datetime import UTC
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

_TABLE_NAME = lambda: os.environ["DYNAMODB_TABLE_TELEMETRY"]  # noqa: E731

_resource = boto3.resource(
    "dynamodb", region_name=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
)


def _table():
    return _resource.Table(_TABLE_NAME())


def write_telemetry(record: dict[str, Any]) -> None:
    """テレメトリ1点を DynamoDB に書き込む (TTL: 24時間)"""
    robot_id = record["robot_id"]
    timestamp = record.get("timestamp", "")

    item = {
        "robot_id": robot_id,
        "timestamp": timestamp,
        "battery_level": Decimal(str(record.get("battery_level", 0))),
        "speed": Decimal(str(record.get("speed", 0))),
        "status": record.get("status", "UNKNOWN"),
        "room": record.get("position", {}).get("room", "unknown"),
        "position_x": Decimal(str(record.get("position", {}).get("x", 0))),
        "position_y": Decimal(str(record.get("position", {}).get("y", 0))),
        "ttl": int(time.time()) + 86400,  # 24時間後に自動削除
    }
    _table().put_item(Item=item)


def query_telemetry(robot_id: str, minutes: int = 60) -> list[dict[str, Any]]:
    """過去 N 分間のテレメトリ一覧を取得"""
    from datetime import datetime, timedelta

    since = (datetime.now(UTC) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = _table().query(
        KeyConditionExpression=Key("robot_id").eq(robot_id) & Key("timestamp").gte(since),
        ScanIndexForward=True,
    )

    rows = []
    for item in resp.get("Items", []):
        rows.append(
            {
                "timestamp": item["timestamp"],
                "battery_level": float(item.get("battery_level", 0)),
                "speed": float(item.get("speed", 0)),
                "status": item.get("status", ""),
            }
        )
    return rows
