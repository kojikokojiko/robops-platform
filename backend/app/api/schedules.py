from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.models.schedule import Schedule, ScheduleCreate
from app.services import dynamodb_service as db
from app.services import scheduler_service as sched

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[Schedule])
def list_schedules() -> list[Schedule]:
    return [Schedule(**item) for item in db.get_all_schedules()]


@router.post("", response_model=Schedule, status_code=201)
def create_schedule(body: ScheduleCreate) -> Schedule:
    schedule_id = str(uuid.uuid4())[:8]

    sched.create_schedule(
        schedule_id=schedule_id,
        robot_id=body.robot_id,
        room_id=body.room_id,
        cron_expression=body.cron_expression,
    )

    item: dict = {
        "schedule_id": schedule_id,
        "robot_id": body.robot_id,
        "room_id": body.room_id,
        "cron_expression": body.cron_expression,
        "description": body.description,
        "enabled": True,
    }
    db.put_schedule(item)
    return Schedule(**item)


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str) -> None:
    items = db.get_all_schedules()
    target = next((i for i in items if i["schedule_id"] == schedule_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Schedule not found")

    sched.delete_schedule(schedule_id)
    db.delete_schedule(schedule_id, target["robot_id"])
