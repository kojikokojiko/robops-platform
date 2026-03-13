from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.robot import CommandResponse, Robot, RobotCommand
from app.services import dynamodb_service as db
from app.services import iot_service as iot

router = APIRouter(prefix="/robots", tags=["robots"])


@router.get("", response_model=list[Robot])
def list_robots() -> list[Robot]:
    items = db.get_all_robots()
    return [Robot(**_normalize(item)) for item in items]


@router.get("/{robot_id}", response_model=Robot)
def get_robot(robot_id: str) -> Robot:
    item = db.get_robot(robot_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return Robot(**_normalize(item))


@router.post("/{robot_id}/commands", response_model=CommandResponse)
def send_command(robot_id: str, body: RobotCommand) -> CommandResponse:
    item = db.get_robot(robot_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")

    iot.publish_command(robot_id, body.command, body.params)
    return CommandResponse(accepted=True, message=f"Command '{body.command}' sent to {robot_id}")


def _normalize(item: dict) -> dict:
    """DynamoDB の Decimal 等を float に変換"""
    from decimal import Decimal
    result = {}
    for k, v in item.items():
        if isinstance(v, Decimal):
            result[k] = float(v)
        elif isinstance(v, dict):
            result[k] = {kk: float(vv) if isinstance(vv, Decimal) else vv for kk, vv in v.items()}
        else:
            result[k] = v
    return result
