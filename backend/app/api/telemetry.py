from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.telemetry import TelemetryHistory, TelemetryPoint
from app.services import timestream_service as ts

router = APIRouter(prefix="/robots", tags=["telemetry"])


@router.get("/{robot_id}/telemetry", response_model=TelemetryHistory)
def get_telemetry(
    robot_id: str,
    minutes: int = Query(default=60, ge=1, le=1440),
) -> TelemetryHistory:
    rows = ts.query_telemetry(robot_id, minutes)

    # Timestream の行を (timestamp, battery_level, speed) に集約
    points_by_time: dict[str, dict] = {}
    for row in rows:
        t = row.get("time", "")
        if t not in points_by_time:
            points_by_time[t] = {"timestamp": t, "battery_level": 0.0, "speed": 0.0, "status": ""}
        name = row.get("measure_name", "")
        val = float(row.get("measure_value::double") or 0)
        if name == "battery_level":
            points_by_time[t]["battery_level"] = val
        elif name == "speed":
            points_by_time[t]["speed"] = val

    points = [TelemetryPoint(**v) for v in sorted(points_by_time.values(), key=lambda x: x["timestamp"])]
    return TelemetryHistory(robot_id=robot_id, points=points)
