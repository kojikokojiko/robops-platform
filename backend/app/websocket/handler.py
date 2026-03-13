"""
WebSocket Lambda ハンドラー。
API Gateway WebSocket の $connect / $disconnect / $default を処理。
ローカル開発では uvicorn の WebSocket エンドポイントとして動作。
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3

from app.services import dynamodb_service as db

logger = logging.getLogger(__name__)

_region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda エントリポイント (API Gateway WebSocket)"""
    route = event.get("requestContext", {}).get("routeKey", "$default")
    connection_id = event.get("requestContext", {}).get("connectionId", "")

    if route == "$connect":
        return _on_connect(connection_id)
    elif route == "$disconnect":
        return _on_disconnect(connection_id)
    else:
        return _on_message(connection_id, event.get("body", "{}"))


def _on_connect(connection_id: str) -> dict[str, Any]:
    ttl = int(time.time()) + 3600  # 1時間後に自動削除
    db.save_connection(connection_id, ttl)
    logger.info("WebSocket connected: %s", connection_id)
    return {"statusCode": 200}


def _on_disconnect(connection_id: str) -> dict[str, Any]:
    db.delete_connection(connection_id)
    logger.info("WebSocket disconnected: %s", connection_id)
    return {"statusCode": 200}


def _on_message(connection_id: str, body: str) -> dict[str, Any]:
    try:
        msg = json.loads(body)
        action = msg.get("action", "")

        if action == "subscribe_robot":
            # 特定ロボットの購読リクエスト (現在は全ロボットの更新を送る設計)
            _send_current_state(connection_id)

    except Exception:
        logger.exception("Error handling WebSocket message from %s", connection_id)

    return {"statusCode": 200}


def _send_current_state(connection_id: str) -> None:
    """現在の全ロボット状態を送信"""
    robots = db.get_all_robots()
    _post_to_connection(
        connection_id,
        {"type": "initial_state", "robots": robots},
    )


def _post_to_connection(connection_id: str, payload: dict[str, Any]) -> None:
    """API Gateway WebSocket 経由でクライアントにメッセージを送信"""
    ws_endpoint = os.getenv("WEBSOCKET_API_ENDPOINT")
    if not ws_endpoint:
        logger.warning("WEBSOCKET_API_ENDPOINT not set, skipping push")
        return

    apigw = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=ws_endpoint,
        region_name=_region,
    )
    try:
        apigw.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(payload),
        )
    except apigw.exceptions.GoneException:
        logger.info("Connection %s is gone, removing", connection_id)
        db.delete_connection(connection_id)
