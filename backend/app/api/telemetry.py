from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.telemetry import TelemetryHistory, TelemetryPoint
from app.services import telemetry_service as ts

router = APIRouter(prefix="/robots", tags=["telemetry"])


@router.get("/{robot_id}/telemetry", response_model=TelemetryHistory)
def get_telemetry(
    robot_id: str,
    minutes: int = Query(default=60, ge=1, le=1440),
) -> TelemetryHistory:
    rows = ts.query_telemetry(robot_id, minutes)
    points = [
        TelemetryPoint(
            timestamp=r["timestamp"],
            battery_level=r["battery_level"],
            speed=r["speed"],
            status=r.get("status", ""),
        )
        for r in rows
    ]
    return TelemetryHistory(robot_id=robot_id, points=points)
