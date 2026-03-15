from __future__ import annotations

import json
import os
import uuid

import boto3
from fastapi import APIRouter, HTTPException

from app.models.ota import OtaJob, OtaJobCreate
from app.services import dynamodb_service as db
from app.services import iot_service as iot
from app.services.iot_service import _now_iso

router = APIRouter(prefix="/ota", tags=["ota"])

_region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
_s3 = boto3.client("s3", region_name=_region)


@router.get("/jobs", response_model=list[OtaJob])
def list_ota_jobs() -> list[OtaJob]:
    items = db.get_all_ota_jobs()
    return [OtaJob(**_normalize(_sync_status(i))) for i in items]


@router.post("/jobs", response_model=list[OtaJob], status_code=201)
def create_ota_job(body: OtaJobCreate) -> list[OtaJob]:
    job_id = f"ota-{uuid.uuid4().hex[:8]}"
    firmware_bucket = os.environ["OTA_FIRMWARE_BUCKET"]

    # S3 にマニフェストをアップロード
    manifest = {
        "version": body.version,
        "max_speed": body.new_speed,
        "description": body.description,
    }
    manifest_key = f"manifests/{job_id}/manifest.json"
    _s3.put_object(
        Bucket=firmware_bucket,
        Key=manifest_key,
        Body=json.dumps(manifest),
        ContentType="application/json",
    )

    # IoT Jobs 作成
    iot.create_ota_job(
        job_id=job_id,
        robot_ids=body.robot_ids,
        new_speed=body.new_speed,
        version=body.version,
        firmware_bucket=firmware_bucket,
        manifest_key=manifest_key,
    )

    # DynamoDB に記録 (ロボットごと)
    results = []
    for robot_id in body.robot_ids:
        item = {
            "job_id": job_id,
            "robot_id": robot_id,
            "status": "QUEUED",
            "firmware_version": body.version,
            "new_speed": str(body.new_speed),
            "progress": 0,
            "started_at": _now_iso(),
            "completed_at": "",
        }
        db.put_ota_job(item)
        results.append(OtaJob(**_normalize(item)))

    return results


@router.get("/jobs/{job_id}", response_model=list[OtaJob])
def get_ota_job(job_id: str) -> list[OtaJob]:
    items = [i for i in db.get_all_ota_jobs() if i["job_id"] == job_id]
    if not items:
        raise HTTPException(status_code=404, detail="OTA job not found")

    return [OtaJob(**_normalize(_sync_status(i))) for i in items]


def _sync_status(item: dict) -> dict:
    """IoT Jobs の実際のステータスで DynamoDB を更新して返す"""
    current = item.get("status", "")
    if current in ("SUCCEEDED", "FAILED", "CANCELED"):
        return item  # 終端状態はそのまま

    iot_status = iot.get_job_execution_status(item["job_id"], item["robot_id"])
    if not iot_status or iot_status == current:
        return item

    # ステータスマッピング (IoT Jobs → DynamoDB)
    status_map = {
        "QUEUED": "QUEUED",
        "IN_PROGRESS": "IN_PROGRESS",
        "SUCCEEDED": "SUCCEEDED",
        "FAILED": "FAILED",
        "CANCELED": "CANCELED",
        "REJECTED": "FAILED",
        "TIMED_OUT": "FAILED",
    }
    new_status = status_map.get(iot_status, current)
    updated = {**item, "status": new_status}
    if new_status in ("SUCCEEDED", "FAILED"):
        updated["completed_at"] = _now_iso()
        updated["progress"] = 100 if new_status == "SUCCEEDED" else item.get("progress", 0)

    db.put_ota_job(updated)
    return updated


def _normalize(item: dict) -> dict:
    from decimal import Decimal
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}
