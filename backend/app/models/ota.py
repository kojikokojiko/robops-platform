from __future__ import annotations

from pydantic import BaseModel, Field


class OtaJobCreate(BaseModel):
    robot_ids: list[str]
    new_speed: float = Field(gt=0, le=2.0, description="新しい最大速度 (m/s)")
    version: str
    description: str = ""


class OtaJob(BaseModel):
    job_id: str
    robot_id: str
    status: str  # QUEUED / IN_PROGRESS / SUCCEEDED / FAILED / CANCELED
    firmware_version: str
    new_speed: float
    progress: int = 0
    started_at: str = ""
    completed_at: str = ""
