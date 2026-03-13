"""
EventBridge Scheduler → Lambda。
スケジュール時刻に START_CLEANING コマンドをロボットに送信。
"""

from __future__ import annotations

import logging
from typing import Any

from app.services import iot_service as iot

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: Any) -> None:
    """
    EventBridge Scheduler が渡す event:
    {
        "robot_id": "robot-001",
        "room_id": "living_room",
        "schedule_id": "abc123"
    }
    """
    robot_id = event.get("robot_id")
    room_id = event.get("room_id")
    schedule_id = event.get("schedule_id")

    if not robot_id or not room_id:
        logger.error("Missing robot_id or room_id in scheduler event: %s", event)
        return

    logger.info("Scheduled cleaning: robot=%s room=%s schedule=%s", robot_id, room_id, schedule_id)
    iot.publish_command(robot_id, "START_CLEANING", {"room_id": room_id})
