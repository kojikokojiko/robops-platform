"""EventBridge Scheduler アクセス層"""

from __future__ import annotations

import os

import boto3

_region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
_scheduler = boto3.client("scheduler", region_name=_region)

_GROUP = lambda: os.getenv("EVENTBRIDGE_SCHEDULE_GROUP", f"robops-{os.getenv('ENV', 'dev')}")  # noqa: E731
_TRIGGER_ARN = lambda: os.environ["SCHEDULER_TRIGGER_LAMBDA_ARN"]  # noqa: E731
_SCHEDULER_ROLE_ARN = lambda: os.environ["EVENTBRIDGE_SCHEDULER_ROLE_ARN"]  # noqa: E731


def create_schedule(
    schedule_id: str,
    robot_id: str,
    room_id: str,
    cron_expression: str,
) -> str:
    """EventBridge Scheduler にスケジュールを登録する"""
    name = f"clean-{schedule_id}"

    _scheduler.create_schedule(
        Name=name,
        GroupName=_GROUP(),
        ScheduleExpression=cron_expression,
        ScheduleExpressionTimezone="Asia/Tokyo",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": _TRIGGER_ARN(),
            "RoleArn": _SCHEDULER_ROLE_ARN(),
            "Input": f'{{"robot_id": "{robot_id}", "room_id": "{room_id}", "schedule_id": "{schedule_id}"}}',
        },
        State="ENABLED",
    )
    return name


def delete_schedule(schedule_id: str) -> None:
    name = f"clean-{schedule_id}"
    try:
        _scheduler.delete_schedule(Name=name, GroupName=_GROUP())
    except _scheduler.exceptions.ResourceNotFoundException:
        pass


def toggle_schedule(schedule_id: str, enabled: bool) -> None:
    name = f"clean-{schedule_id}"
    resp = _scheduler.get_schedule(Name=name, GroupName=_GROUP())

    _scheduler.update_schedule(
        Name=name,
        GroupName=_GROUP(),
        ScheduleExpression=resp["ScheduleExpression"],
        ScheduleExpressionTimezone=resp.get("ScheduleExpressionTimezone", "Asia/Tokyo"),
        FlexibleTimeWindow=resp["FlexibleTimeWindow"],
        Target=resp["Target"],
        State="ENABLED" if enabled else "DISABLED",
    )
