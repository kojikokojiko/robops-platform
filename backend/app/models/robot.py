from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RobotStatus(StrEnum):
    IDLE = "IDLE"
    CLEANING = "CLEANING"
    CHARGING = "CHARGING"
    RETURNING_TO_DOCK = "RETURNING_TO_DOCK"
    LOW_BATTERY = "LOW_BATTERY"
    UPDATING = "UPDATING"
    ERROR = "ERROR"


class Position(BaseModel):
    x: float
    y: float
    room: str


class Robot(BaseModel):
    robot_id: str
    name: str = ""
    status: RobotStatus = RobotStatus.IDLE
    battery_level: float = 100.0
    position: Position = Field(default_factory=lambda: Position(x=0.5, y=0.5, room="charging_dock"))
    speed: float = 0.0
    firmware_version: str = "1.0.0"
    last_seen: str = ""
    error_code: str | None = None


class RobotCommand(BaseModel):
    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class CommandResponse(BaseModel):
    accepted: bool
    message: str = ""
