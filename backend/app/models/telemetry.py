from __future__ import annotations

from pydantic import BaseModel


class TelemetryPoint(BaseModel):
    timestamp: str
    battery_level: float
    speed: float
    status: str


class TelemetryHistory(BaseModel):
    robot_id: str
    points: list[TelemetryPoint]
