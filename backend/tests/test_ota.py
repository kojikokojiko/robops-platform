"""OTA ジョブ API の結合テスト (IoT Jobs はモック、S3 は moto)"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup(aws_mock):  # noqa: ANN001
    """conftest.aws_mock を全テストで有効化"""


# ─── GET /ota/jobs ────────────────────────────────────────

def test_list_ota_jobs_empty():
    resp = client.get("/ota/jobs")
    assert resp.status_code == 200
    assert resp.json() == []


# ─── POST /ota/jobs ───────────────────────────────────────

@patch("app.services.iot_service._get_account_id", return_value="123456789012")
@patch("app.services.iot_service._iot_client")
def test_create_ota_job(mock_iot_client_fn, _mock_account):
    mock_iot = mock_iot_client_fn.return_value
    mock_iot.create_job.return_value = {"jobId": "ota-test1234"}

    resp = client.post("/ota/jobs", json={
        "robot_ids": ["robot-001", "robot-002"],
        "version": "2.0.0",
        "new_speed": 1.5,
        "description": "速度アップ",
    })

    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    robot_ids = {item["robot_id"] for item in data}
    assert robot_ids == {"robot-001", "robot-002"}
    for item in data:
        assert item["status"] == "QUEUED"
        assert item["firmware_version"] == "2.0.0"
        assert abs(item["new_speed"] - 1.5) < 0.001

    mock_iot.create_job.assert_called_once()


@patch("app.services.iot_service._get_account_id", return_value="123456789012")
@patch("app.services.iot_service._iot_client")
def test_create_ota_job_uploads_manifest(mock_iot_client_fn, _mock_account):
    """S3 にマニフェストが実際にアップロードされること"""
    import boto3
    mock_iot_client_fn.return_value.create_job.return_value = {"jobId": "ota-abc"}

    client.post("/ota/jobs", json={
        "robot_ids": ["robot-001"],
        "version": "3.0.0",
        "new_speed": 0.8,
        "description": "",
    })

    s3 = boto3.client("s3", region_name="ap-northeast-1")
    objects = s3.list_objects_v2(Bucket="test-firmware-bucket", Prefix="manifests/")
    assert objects.get("KeyCount", 0) == 1


# ─── GET /ota/jobs/{job_id} ──────────────────────────────

@patch("app.services.iot_service._get_account_id", return_value="123456789012")
@patch("app.services.iot_service._iot_client")
def test_get_ota_job(mock_iot_client_fn, _mock_account):
    mock_iot = mock_iot_client_fn.return_value
    mock_iot.create_job.return_value = {"jobId": "ota-xyz"}
    mock_iot.describe_job.return_value = {"job": {"status": "QUEUED"}}

    create_resp = client.post("/ota/jobs", json={
        "robot_ids": ["robot-001"],
        "version": "1.1.0",
        "new_speed": 1.0,
        "description": "",
    })
    job_id = create_resp.json()[0]["job_id"]

    get_resp = client.get(f"/ota/jobs/{job_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert len(data) == 1
    assert data[0]["job_id"] == job_id


@patch("app.services.iot_service._iot_client")
def test_get_nonexistent_ota_job(mock_iot_client_fn):
    mock_iot_client_fn.return_value.describe_job.side_effect = Exception("not found")
    resp = client.get("/ota/jobs/nonexistent-job-id")
    assert resp.status_code == 404


@patch("app.services.iot_service._get_account_id", return_value="123456789012")
@patch("app.services.iot_service._iot_client")
def test_list_ota_jobs_after_create(mock_iot_client_fn, _mock_account):
    mock_iot_client_fn.return_value.create_job.return_value = {"jobId": "ota-list"}

    client.post("/ota/jobs", json={
        "robot_ids": ["robot-001", "robot-002", "robot-003"],
        "version": "1.5.0",
        "new_speed": 1.2,
        "description": "",
    })

    resp = client.get("/ota/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 3
