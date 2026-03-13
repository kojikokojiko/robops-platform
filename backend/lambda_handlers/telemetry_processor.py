"""
IoT Topic Rule → Lambda。
robots/+/telemetry メッセージを DynamoDB と Timestream に書き込む。
"""

from __future__ import annotations

import logging
from typing import Any

from app.services import dynamodb_service as db
from app.services import timestream_service as ts

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

    # DynamoDB にロボット状態を upsert
    robot_item = {
        "robot_id": robot_id,
        "status": event.get("status", "UNKNOWN"),
        "battery_level": _to_decimal(event.get("battery_level", 0)),
        "position": event.get("position", {}),
        "speed": _to_decimal(event.get("speed", 0)),
        "firmware_version": event.get("firmware_version", "unknown"),
        "last_seen": event.get("timestamp", ""),
        "error_code": event.get("error_code"),
    }
    db.upsert_robot(robot_item)

    # Timestream に時系列データを書き込む
    try:
        ts.write_telemetry(event)
    except Exception:
        logger.exception("Failed to write telemetry to Timestream for %s", robot_id)


def _to_decimal(value: Any) -> Any:
    from decimal import Decimal
    try:
        return Decimal(str(value))
    except Exception:
        return value
