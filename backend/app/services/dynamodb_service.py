"""DynamoDB アクセス層"""

from __future__ import annotations

import os
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

_dynamodb = boto3.resource(
    "dynamodb", region_name=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
)


def _table(name_env: str) -> Any:
    return _dynamodb.Table(os.environ[name_env])


# ─── Robots ──────────────────────────────────────────────


def get_all_robots() -> list[dict[str, Any]]:
    table = _table("DYNAMODB_TABLE_ROBOTS")
    resp = table.scan()
    return resp.get("Items", [])


def get_robot(robot_id: str) -> dict[str, Any] | None:
    table = _table("DYNAMODB_TABLE_ROBOTS")
    resp = table.get_item(Key={"robot_id": robot_id})
    return resp.get("Item")


def upsert_robot(item: dict[str, Any]) -> None:
    table = _table("DYNAMODB_TABLE_ROBOTS")
    table.put_item(Item=item)


def get_robots_by_status(status: str) -> list[dict[str, Any]]:
    table = _table("DYNAMODB_TABLE_ROBOTS")
    resp = table.query(
        IndexName="status-index",
        KeyConditionExpression=Key("status").eq(status),
    )
    return resp.get("Items", [])


# ─── Schedules ────────────────────────────────────────────


def get_all_schedules() -> list[dict[str, Any]]:
    table = _table("DYNAMODB_TABLE_SCHEDULES")
    return table.scan().get("Items", [])


def get_schedules_by_robot(robot_id: str) -> list[dict[str, Any]]:
    table = _table("DYNAMODB_TABLE_SCHEDULES")
    resp = table.query(
        IndexName="robot-index",
        KeyConditionExpression=Key("robot_id").eq(robot_id),
    )
    return resp.get("Items", [])


def put_schedule(item: dict[str, Any]) -> None:
    _table("DYNAMODB_TABLE_SCHEDULES").put_item(Item=item)


def delete_schedule(schedule_id: str, robot_id: str) -> None:
    _table("DYNAMODB_TABLE_SCHEDULES").delete_item(
        Key={"schedule_id": schedule_id, "robot_id": robot_id}
    )


# ─── OTA Jobs ─────────────────────────────────────────────


def get_ota_jobs_by_robot(robot_id: str) -> list[dict[str, Any]]:
    table = _table("DYNAMODB_TABLE_OTA_JOBS")
    resp = table.query(
        IndexName="robot-index",
        KeyConditionExpression=Key("robot_id").eq(robot_id),
    )
    return resp.get("Items", [])


def put_ota_job(item: dict[str, Any]) -> None:
    _table("DYNAMODB_TABLE_OTA_JOBS").put_item(Item=item)


def get_all_ota_jobs() -> list[dict[str, Any]]:
    return _table("DYNAMODB_TABLE_OTA_JOBS").scan().get("Items", [])


# ─── WebSocket Connections ────────────────────────────────


def save_connection(connection_id: str, ttl: int) -> None:
    _table("DYNAMODB_TABLE_WS_CONNECTIONS").put_item(
        Item={"connection_id": connection_id, "ttl": ttl}
    )


def delete_connection(connection_id: str) -> None:
    _table("DYNAMODB_TABLE_WS_CONNECTIONS").delete_item(Key={"connection_id": connection_id})


def get_all_connections() -> list[str]:
    items = _table("DYNAMODB_TABLE_WS_CONNECTIONS").scan().get("Items", [])
    return [item["connection_id"] for item in items]
