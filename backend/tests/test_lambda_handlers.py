"""Lambda ハンドラーの結合テスト"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services import dynamodb_service as db


@pytest.fixture(autouse=True)
def setup(aws_mock):  # noqa: ANN001
    """conftest.aws_mock を全テストで有効化"""


# ─── telemetry_processor ─────────────────────────────────


class TestTelemetryProcessor:
    """IoT → DynamoDB upsert + Timestream 書き込み"""

    @patch("app.services.timestream_service.write_telemetry")
    def test_upserts_robot_state(self, mock_ts):
        from lambda_handlers.telemetry_processor import handler

        event = {
            "robot_id": "robot-001",
            "status": "CLEANING",
            "battery_level": 75.5,
            "speed": 1.2,
            "position": {"x": 3.0, "y": 4.0, "room": "living_room"},
            "firmware_version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        handler(event, None)

        robot = db.get_robot("robot-001")
        assert robot is not None
        assert robot["status"] == "CLEANING"
        assert float(robot["battery_level"]) == pytest.approx(75.5)
        assert float(robot["speed"]) == pytest.approx(1.2)
        assert robot["firmware_version"] == "1.0.0"
        mock_ts.assert_called_once_with(event)

    @patch("app.services.timestream_service.write_telemetry")
    def test_overwrites_existing_robot(self, mock_ts):
        from lambda_handlers.telemetry_processor import handler

        for status in ("IDLE", "CLEANING"):
            handler(
                {
                    "robot_id": "robot-002",
                    "status": status,
                    "battery_level": 90.0,
                    "speed": 0.0,
                    "position": {"x": 0.0, "y": 0.0, "room": "charging_dock"},
                    "firmware_version": "1.0.0",
                    "timestamp": "2024-01-01T00:00:00Z",
                },
                None,
            )

        robot = db.get_robot("robot-002")
        assert robot["status"] == "CLEANING"

    @patch("app.services.timestream_service.write_telemetry")
    def test_missing_robot_id_is_ignored(self, mock_ts):
        from lambda_handlers.telemetry_processor import handler

        handler({"status": "IDLE"}, None)  # robot_id なし → 何もしない

        robots = db.get_all_robots()
        assert robots == []
        mock_ts.assert_not_called()

    @patch("app.services.timestream_service.write_telemetry", side_effect=Exception("ts error"))
    def test_timestream_failure_does_not_raise(self, mock_ts):
        """Timestream 書き込み失敗でも DynamoDB は成功する"""
        from lambda_handlers.telemetry_processor import handler

        handler(
            {
                "robot_id": "robot-003",
                "status": "ERROR",
                "battery_level": 10.0,
                "speed": 0.0,
                "position": {"x": 1.0, "y": 1.0, "room": "bedroom_1"},
                "firmware_version": "1.0.0",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            None,
        )

        robot = db.get_robot("robot-003")
        assert robot is not None
        assert robot["status"] == "ERROR"


# ─── websocket_broadcaster ───────────────────────────────


class TestWebSocketBroadcaster:
    """DynamoDB Streams → WebSocket 全接続ブロードキャスト"""

    def _make_stream_record(self, robot_id: str, status: str) -> dict:
        """DynamoDB Stream レコードを模倣する NewImage 形式"""
        return {
            "eventName": "MODIFY",
            "dynamodb": {
                "NewImage": {
                    "robot_id": {"S": robot_id},
                    "status": {"S": status},
                    "battery_level": {"N": "80.0"},
                    "speed": {"N": "1.0"},
                    "firmware_version": {"S": "1.0.0"},
                    "position": {
                        "M": {
                            "x": {"N": "1.0"},
                            "y": {"N": "2.0"},
                            "room": {"S": "living_room"},
                        }
                    },
                }
            },
        }

    @patch.dict(
        "os.environ",
        {"WEBSOCKET_API_ENDPOINT": "https://fake.execute-api.ap-northeast-1.amazonaws.com/dev"},
    )
    @patch("boto3.client")
    def test_broadcasts_to_all_connections(self, mock_boto_client):
        from lambda_handlers.websocket_broadcaster import handler

        # 2 接続を DynamoDB に登録
        db.save_connection("conn-aaa", ttl=9999999999)
        db.save_connection("conn-bbb", ttl=9999999999)

        mock_apigw = MagicMock()
        mock_boto_client.return_value = mock_apigw

        event = {"Records": [self._make_stream_record("robot-001", "CLEANING")]}
        handler(event, None)

        assert mock_apigw.post_to_connection.call_count == 2
        call_cids = {
            call.kwargs["ConnectionId"] for call in mock_apigw.post_to_connection.call_args_list
        }
        assert call_cids == {"conn-aaa", "conn-bbb"}

    @patch.dict(
        "os.environ",
        {"WEBSOCKET_API_ENDPOINT": "https://fake.execute-api.ap-northeast-1.amazonaws.com/dev"},
    )
    @patch("boto3.client")
    def test_skips_on_delete_event(self, mock_boto_client):
        """DELETE イベントはブロードキャストしない"""
        from lambda_handlers.websocket_broadcaster import handler

        db.save_connection("conn-ccc", ttl=9999999999)
        mock_apigw = MagicMock()
        mock_boto_client.return_value = mock_apigw

        event = {"Records": [{"eventName": "REMOVE", "dynamodb": {"OldImage": {}}}]}
        handler(event, None)

        mock_apigw.post_to_connection.assert_not_called()

    @patch.dict(
        "os.environ",
        {"WEBSOCKET_API_ENDPOINT": "https://fake.execute-api.ap-northeast-1.amazonaws.com/dev"},
    )
    @patch("boto3.client")
    def test_removes_stale_connections(self, mock_boto_client):
        """GoneException が発生した接続は DynamoDB から削除される"""
        from lambda_handlers.websocket_broadcaster import handler

        db.save_connection("conn-stale", ttl=9999999999)

        mock_apigw = MagicMock()
        gone_exc = type("GoneException", (Exception,), {})
        mock_apigw.exceptions.GoneException = gone_exc
        mock_apigw.post_to_connection.side_effect = gone_exc("gone")
        mock_boto_client.return_value = mock_apigw

        event = {"Records": [self._make_stream_record("robot-001", "IDLE")]}
        handler(event, None)

        # 接続が DynamoDB から消えていること
        connections = db.get_all_connections()
        assert "conn-stale" not in connections

    def test_no_endpoint_env_returns_early(self):
        """WEBSOCKET_API_ENDPOINT 未設定 → 何もしない"""
        from lambda_handlers.websocket_broadcaster import handler

        with patch.dict("os.environ", {}, clear=True):
            # 環境変数を削除しても例外を投げないこと
            os.environ.pop("WEBSOCKET_API_ENDPOINT", None)
            event = {"Records": [self._make_stream_record("robot-001", "IDLE")]}
            handler(event, None)  # GoneException なし


# ─── scheduler_trigger ───────────────────────────────────


class TestSchedulerTrigger:
    """EventBridge → IoT START_CLEANING コマンド送信"""

    @patch("app.services.iot_service._iot_data_client")
    def test_publishes_start_cleaning(self, mock_iot_client_fn):
        from lambda_handlers.scheduler_trigger import handler

        mock_iot = MagicMock()
        mock_iot_client_fn.return_value = mock_iot

        event = {
            "robot_id": "robot-001",
            "room_id": "kitchen",
            "schedule_id": "abc12345",
        }
        handler(event, None)

        mock_iot.publish.assert_called_once()
        call_kwargs = mock_iot.publish.call_args.kwargs
        assert call_kwargs["topic"] == "robots/robot-001/commands"
        payload = json.loads(call_kwargs["payload"])
        assert payload["command"] == "START_CLEANING"
        assert payload["params"]["room_id"] == "kitchen"

    @patch("app.services.iot_service._iot_data_client")
    def test_missing_fields_does_not_publish(self, mock_iot_client_fn):
        """robot_id か room_id がないときは IoT に送らない"""
        from lambda_handlers.scheduler_trigger import handler

        mock_iot = MagicMock()
        mock_iot_client_fn.return_value = mock_iot

        handler({"room_id": "kitchen"}, None)  # robot_id なし
        handler({"robot_id": "robot-001"}, None)  # room_id なし

        mock_iot.publish.assert_not_called()


import os  # noqa: E402 (末尾 import はテスト内 patch.dict のため)
