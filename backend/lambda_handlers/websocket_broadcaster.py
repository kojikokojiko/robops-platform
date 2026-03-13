"""
DynamoDB Streams → Lambda。
robots テーブルの変更を全 WebSocket クライアントにブロードキャスト。
"""

from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.types import TypeDeserializer

from app.services import dynamodb_service as db

logger = logging.getLogger(__name__)

_region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
_deserializer = TypeDeserializer()


def handler(event: dict[str, Any], context: Any) -> None:
    ws_endpoint = os.getenv("WEBSOCKET_API_ENDPOINT")
    if not ws_endpoint:
        logger.warning("WEBSOCKET_API_ENDPOINT not set")
        return

    apigw = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=ws_endpoint,
        region_name=_region,
    )

    connection_ids = db.get_all_connections()
    if not connection_ids:
        return

    for record in event.get("Records", []):
        if record["eventName"] not in ("INSERT", "MODIFY"):
            continue

        new_image = record["dynamodb"].get("NewImage", {})
        robot_data = {k: _deserializer.deserialize(v) for k, v in new_image.items()}

        payload = json.dumps({"type": "robot_update", "robot": robot_data}, default=_json_default)

        _broadcast(apigw, connection_ids, payload)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _broadcast(apigw: Any, connection_ids: list[str], payload: str) -> None:
    stale = []
    for cid in connection_ids:
        try:
            apigw.post_to_connection(ConnectionId=cid, Data=payload)
        except apigw.exceptions.GoneException:
            stale.append(cid)
        except Exception:
            logger.exception("Failed to post to connection %s", cid)

    for cid in stale:
        db.delete_connection(cid)
