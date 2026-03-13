"""FastAPI エンドポイントのテスト (moto で AWS をモック)"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# テスト用環境変数を設定 (import より前に)
os.environ.update({
    "ENV": "test",
    "AWS_DEFAULT_REGION": "ap-northeast-1",
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "DYNAMODB_TABLE_ROBOTS": "test-robots",
    "DYNAMODB_TABLE_SCHEDULES": "test-schedules",
    "DYNAMODB_TABLE_OTA_JOBS": "test-ota-jobs",
    "DYNAMODB_TABLE_WS_CONNECTIONS": "test-ws-connections",
    "TIMESTREAM_DATABASE": "test-db",
    "TIMESTREAM_TABLE": "telemetry",
    "OTA_FIRMWARE_BUCKET": "test-firmware-bucket",
    "IOT_ENDPOINT": "test.iot.ap-northeast-1.amazonaws.com",
})

import boto3
import moto

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def aws_mock():
    """全テストで DynamoDB・IoT・S3 をモック"""
    with moto.mock_aws():
        _setup_dynamodb()
        yield


def _setup_dynamodb():
    ddb = boto3.resource("dynamodb", region_name="ap-northeast-1")

    ddb.create_table(
        TableName="test-robots",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "robot_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "robot_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "status-index",
            "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )

    ddb.create_table(
        TableName="test-schedules",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "schedule_id", "KeyType": "HASH"},
            {"AttributeName": "robot_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "schedule_id", "AttributeType": "S"},
            {"AttributeName": "robot_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "robot-index",
            "KeySchema": [{"AttributeName": "robot_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )

    ddb.create_table(
        TableName="test-ota-jobs",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "job_id", "KeyType": "HASH"},
            {"AttributeName": "robot_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "job_id", "AttributeType": "S"},
            {"AttributeName": "robot_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "robot-index",
            "KeySchema": [{"AttributeName": "robot_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )

    ddb.create_table(
        TableName="test-ws-connections",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "connection_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connection_id", "AttributeType": "S"}],
    )


# ─── /health ─────────────────────────────────────────────

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── /robots ─────────────────────────────────────────────

def test_list_robots_empty():
    resp = client.get("/robots")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_robots_with_data():
    ddb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    table = ddb.Table("test-robots")
    table.put_item(Item={
        "robot_id": "robot-001",
        "status": "IDLE",
        "battery_level": "85.5",
        "position": {"x": "1.0", "y": "2.0", "room": "living_room"},
        "speed": "0.0",
        "firmware_version": "1.0.0",
        "last_seen": "2024-01-01T00:00:00Z",
    })

    resp = client.get("/robots")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["robot_id"] == "robot-001"


def test_get_robot_not_found():
    resp = client.get("/robots/nonexistent")
    assert resp.status_code == 404


def test_get_robot_found():
    ddb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    ddb.Table("test-robots").put_item(Item={
        "robot_id": "robot-002",
        "status": "CLEANING",
        "battery_level": "70.0",
        "position": {"x": "3.0", "y": "3.0", "room": "kitchen"},
        "speed": "0.5",
        "firmware_version": "1.0.0",
        "last_seen": "2024-01-01T00:00:00Z",
    })

    resp = client.get("/robots/robot-002")
    assert resp.status_code == 200
    assert resp.json()["robot_id"] == "robot-002"
    assert resp.json()["status"] == "CLEANING"


def test_send_command():
    ddb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    ddb.Table("test-robots").put_item(Item={
        "robot_id": "robot-001",
        "status": "IDLE",
        "battery_level": "100.0",
        "position": {"x": "0.5", "y": "0.5", "room": "charging_dock"},
        "speed": "0.0",
        "firmware_version": "1.0.0",
        "last_seen": "",
    })

    with patch("app.services.iot_service._iot_data_client") as mock_client:
        mock_iot = MagicMock()
        mock_client.return_value = mock_iot

        resp = client.post(
            "/robots/robot-001/commands",
            json={"command": "START_CLEANING", "params": {"room_id": "living_room"}},
        )

    assert resp.status_code == 200
    assert resp.json()["accepted"] is True


# ─── /schedules ──────────────────────────────────────────

def test_list_schedules_empty():
    resp = client.get("/schedules")
    assert resp.status_code == 200
    assert resp.json() == []
