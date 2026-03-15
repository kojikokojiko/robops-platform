"""AWS IoT Core アクセス層"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3

_region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")


@lru_cache(maxsize=1)
def _iot_data_client() -> Any:
    endpoint = os.getenv("IOT_ENDPOINT")
    kwargs = {"region_name": _region}
    if endpoint:
        kwargs["endpoint_url"] = f"https://{endpoint}"
    return boto3.client("iot-data", **kwargs)


@lru_cache(maxsize=1)
def _iot_client() -> Any:
    return boto3.client("iot", region_name=_region)


def publish_command(robot_id: str, command: str, params: dict[str, Any] | None = None) -> None:
    """ロボットにコマンドを送信する"""

    payload = {
        "command": command,
        "params": params or {},
        "issued_by": "dashboard",
        "timestamp": _now_iso(),
    }
    _iot_data_client().publish(
        topic=f"robots/{robot_id}/commands",
        qos=1,
        payload=json.dumps(payload),
    )


def create_ota_job(
    job_id: str,
    robot_ids: list[str],
    new_speed: float,
    version: str,
    firmware_bucket: str,
    manifest_key: str,
) -> str:
    """IoT Jobs で OTA ジョブを作成する"""
    client = _iot_client()

    job_doc = {
        "version": version,
        "max_speed": new_speed,
        "manifest_s3_key": manifest_key,
    }

    targets = [f"arn:aws:iot:{_region}:{_get_account_id()}:thing/{rid}" for rid in robot_ids]

    resp = client.create_job(
        jobId=job_id,
        targets=targets,
        document=json.dumps(job_doc),
        description=f"OTA: speed={new_speed} version={version}",
        targetSelection="SNAPSHOT",
    )
    return resp["jobId"]


def get_job_status(job_id: str) -> dict[str, Any]:
    resp = _iot_client().describe_job(jobId=job_id)
    return resp.get("job", {})


def get_job_execution_status(job_id: str, robot_id: str) -> str | None:
    """ロボットごとの IoT Job 実行ステータスを取得"""
    try:
        resp = _iot_client().describe_job_execution(jobId=job_id, thingName=robot_id)
        return resp.get("execution", {}).get("status")
    except Exception:
        return None


def list_things() -> list[dict[str, Any]]:
    resp = _iot_client().list_things()
    return resp.get("things", [])


def _get_account_id() -> str:
    return boto3.client("sts", region_name=_region).get_caller_identity()["Account"]


def _now_iso() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
