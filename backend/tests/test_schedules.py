"""スケジュール API の結合テスト (EventBridge Scheduler はモック)"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup(aws_mock):  # noqa: ANN001
    """conftest.aws_mock を全テストで有効化"""


# ─── GET /schedules ────────────────────────────────────────

def test_list_schedules_empty():
    resp = client.get("/schedules")
    assert resp.status_code == 200
    assert resp.json() == []


# ─── POST /schedules ──────────────────────────────────────

@patch("app.services.scheduler_service._scheduler")
def test_create_schedule(mock_sched):
    mock_sched.create_schedule.return_value = {}

    resp = client.post("/schedules", json={
        "robot_id": "robot-001",
        "room_id": "living_room",
        "cron_expression": "cron(0 8 * * ? *)",
        "description": "毎朝8時",
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["robot_id"] == "robot-001"
    assert data["room_id"] == "living_room"
    assert data["cron_expression"] == "cron(0 8 * * ? *)"
    assert data["description"] == "毎朝8時"
    assert data["enabled"] is True
    assert "schedule_id" in data
    mock_sched.create_schedule.assert_called_once()


@patch("app.services.scheduler_service._scheduler")
def test_create_schedule_persisted(mock_sched):
    """作成後に一覧に現れることを確認"""
    mock_sched.create_schedule.return_value = {}

    client.post("/schedules", json={
        "robot_id": "robot-002",
        "room_id": "kitchen",
        "cron_expression": "cron(0 9 * * ? *)",
        "description": "",
    })

    resp = client.get("/schedules")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["robot_id"] == "robot-002"


# ─── DELETE /schedules/{id} ───────────────────────────────

@patch("app.services.scheduler_service._scheduler")
def test_delete_schedule(mock_sched):
    mock_sched.create_schedule.return_value = {}
    mock_sched.delete_schedule.return_value = {}

    # 作成
    create_resp = client.post("/schedules", json={
        "robot_id": "robot-001",
        "room_id": "bedroom_1",
        "cron_expression": "cron(0 10 * * ? *)",
        "description": "",
    })
    schedule_id = create_resp.json()["schedule_id"]

    # 削除
    del_resp = client.delete(f"/schedules/{schedule_id}")
    assert del_resp.status_code == 204

    # 一覧が空に戻ること
    list_resp = client.get("/schedules")
    assert list_resp.json() == []


@patch("app.services.scheduler_service._scheduler")
def test_delete_nonexistent_schedule(mock_sched):  # noqa: ARG001
    resp = client.delete("/schedules/nonexistent-id")
    assert resp.status_code == 404


@patch("app.services.scheduler_service._scheduler")
def test_create_multiple_schedules(mock_sched):
    mock_sched.create_schedule.return_value = {}

    for i in range(3):
        client.post("/schedules", json={
            "robot_id": f"robot-00{i+1}",
            "room_id": "living_room",
            "cron_expression": "cron(0 8 * * ? *)",
            "description": "",
        })

    resp = client.get("/schedules")
    assert len(resp.json()) == 3
