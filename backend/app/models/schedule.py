from __future__ import annotations

from pydantic import BaseModel


class Schedule(BaseModel):
    schedule_id: str = ""
    robot_id: str
    room_id: str
    cron_expression: str  # EventBridge cron形式 e.g. "cron(0 8 * * ? *)"
    enabled: bool = True
    description: str = ""


class ScheduleCreate(BaseModel):
    robot_id: str
    room_id: str
    cron_expression: str
    description: str = ""
