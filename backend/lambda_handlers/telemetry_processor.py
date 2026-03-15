"""
IoT Topic Rule → Lambda。
robots/+/telemetry メッセージを DynamoDB に書き込む。
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from app.services import dynamodb_service as db
from app.services import telemetry_service as ts

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: Any) -> None:
    """
    IoT Rule から直接呼ばれる。
    event = テレメトリペイロード (robots/{id}/telemetry の JSON)
    """
    robot_id = event.get("robot_id")
    if not robot_id:
        logger.warning("Missing robot_id in telemetry event: %s", event)
        return

    # DynamoDB にロボット現在状態を upsert
    raw_pos = event.get("position", {})
    robot_item = {
        "robot_id": robot_id,
        "status": event.get("status", "UNKNOWN"),
        "battery_level": _to_decimal(event.get("battery_level", 0)),
        "position": {k: _to_decimal(v) for k, v in raw_pos.items()},
        "speed": _to_decimal(event.get("speed", 0)),
        "firmware_version": event.get("firmware_version", "unknown"),
        "last_seen": event.get("timestamp", ""),
        "error_code": event.get("error_code"),
    }
    db.upsert_robot(robot_item)

    # DynamoDB にテレメトリ履歴を書き込む
    try:
        ts.write_telemetry(event)
    except Exception:
        logger.exception("Failed to write telemetry history for %s", robot_id)


def _to_decimal(value: Any) -> Any:
    try:
        return Decimal(str(value))
    except Exception:
        return value
