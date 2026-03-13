"""
AWS IoT Core MQTT クライアント。
テレメトリ送信・コマンド受信・OTA Jobs 処理を担当。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from awscrt import mqtt
from awsiot import iotjobs, mqtt_connection_builder

from .robot_state import RobotState

logger = logging.getLogger(__name__)


class RobotMqttClient:
    def __init__(
        self,
        robot_id: str,
        iot_endpoint: str,
        cert_path: str,
        key_path: str,
        ca_path: str,
        telemetry_interval: float = 1.0,
    ) -> None:
        self.robot_id = robot_id
        self.iot_endpoint = iot_endpoint
        self.telemetry_interval = telemetry_interval

        self._conn = mqtt_connection_builder.mtls_from_path(
            endpoint=iot_endpoint,
            cert_filepath=cert_path,
            pri_key_filepath=key_path,
            ca_filepath=ca_path,
            client_id=robot_id,
            clean_session=False,
            keep_alive_secs=30,
            on_connection_interrupted=self._on_connection_interrupted,
            on_connection_resumed=self._on_connection_resumed,
        )

        self._jobs_client = iotjobs.IotJobsClient(self._conn)
        self._state: RobotState | None = None
        self._running = False
        self._telemetry_thread: threading.Thread | None = None

    # ─── トピック名 ────────────────────────────────────────

    @property
    def _telemetry_topic(self) -> str:
        return f"robots/{self.robot_id}/telemetry"

    @property
    def _status_topic(self) -> str:
        return f"robots/{self.robot_id}/status"

    @property
    def _commands_topic(self) -> str:
        return f"robots/{self.robot_id}/commands"

    # ─── 接続 ──────────────────────────────────────────────

    def connect(self, state: RobotState) -> None:
        self._state = state
        logger.info("[%s] Connecting to %s ...", self.robot_id, self.iot_endpoint)

        connect_future = self._conn.connect()
        connect_future.result(timeout=10)
        logger.info("[%s] Connected", self.robot_id)

        self._publish_status("online")
        self._subscribe_commands()
        self._subscribe_jobs()

    def disconnect(self) -> None:
        self._running = False
        if self._telemetry_thread:
            self._telemetry_thread.join(timeout=5)
        self._publish_status("offline")
        disconnect_future = self._conn.disconnect()
        disconnect_future.result(timeout=5)
        logger.info("[%s] Disconnected", self.robot_id)

    # ─── メインループ ──────────────────────────────────────

    def run_forever(self) -> None:
        """テレメトリ送信ループをブロッキングで実行"""
        self._running = True
        logger.info("[%s] Starting telemetry loop (interval=%.1fs)", self.robot_id, self.telemetry_interval)

        while self._running:
            start = time.time()
            try:
                if self._state:
                    self._state.tick()
                    self._publish_telemetry()
            except Exception:
                logger.exception("[%s] Error in telemetry loop", self.robot_id)

            elapsed = time.time() - start
            sleep_time = max(0.0, self.telemetry_interval - elapsed)
            time.sleep(sleep_time)

    # ─── 送信 ──────────────────────────────────────────────

    def _publish_telemetry(self) -> None:
        if not self._state:
            return
        payload = self._state.to_telemetry()
        self._publish(self._telemetry_topic, payload)
        logger.debug("[%s] telemetry: %s", self.robot_id, payload)

    def _publish_status(self, status: str) -> None:
        self._publish(self._status_topic, {"robot_id": self.robot_id, "status": status})

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        self._conn.publish(
            topic=topic,
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )

    # ─── コマンド受信 ──────────────────────────────────────

    def _subscribe_commands(self) -> None:
        subscribe_future, _ = self._conn.subscribe(
            topic=self._commands_topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self._on_command_received,
        )
        subscribe_future.result(timeout=5)
        logger.info("[%s] Subscribed to %s", self.robot_id, self._commands_topic)

    def _on_command_received(self, topic: str, payload: bytes, **kwargs: Any) -> None:
        try:
            msg = json.loads(payload)
            command = msg.get("command", "")
            params = msg.get("params", {})
            logger.info("[%s] Received command: %s params=%s", self.robot_id, command, params)

            if self._state:
                accepted = self._state.handle_command(command, params)
                if not accepted:
                    logger.warning("[%s] Command '%s' was rejected (current status: %s)", self.robot_id, command, self._state.status)
        except Exception:
            logger.exception("[%s] Error handling command", self.robot_id)

    # ─── IoT Jobs (OTA) ───────────────────────────────────

    def _subscribe_jobs(self) -> None:
        # ペンディング中のジョブ通知を購読
        future, _ = self._jobs_client.subscribe_to_get_pending_job_executions_response(
            request=iotjobs.GetPendingJobExecutionsSubscriptionRequest(thing_name=self.robot_id),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self._on_pending_jobs_response,
        )
        future.result(timeout=5)

        # 次のジョブ通知
        future2, _ = self._jobs_client.subscribe_to_start_next_pending_job_execution_accepted(
            request=iotjobs.StartNextJobExecutionSubscriptionRequest(thing_name=self.robot_id),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self._on_next_job,
        )
        future2.result(timeout=5)

        # ジョブ更新完了通知
        future3, _ = self._jobs_client.subscribe_to_update_job_execution_accepted(
            request=iotjobs.UpdateJobExecutionSubscriptionRequest(
                thing_name=self.robot_id, job_id="+",
            ),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=lambda response: logger.debug("[%s] Job update accepted", self.robot_id),
        )
        future3.result(timeout=5)

        # ペンディング中のジョブを取得
        self._jobs_client.get_pending_job_executions(
            request=iotjobs.GetPendingJobExecutionsRequest(thing_name=self.robot_id),
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )

        logger.info("[%s] Subscribed to IoT Jobs", self.robot_id)

    def _on_pending_jobs_response(self, response: iotjobs.GetPendingJobExecutionsResponse) -> None:
        if response.queued_jobs:
            logger.info("[%s] %d pending OTA job(s) found", self.robot_id, len(response.queued_jobs))
            self._start_next_job()

    def _on_next_job(self, response: iotjobs.StartNextJobExecutionResponse) -> None:
        if not response.execution:
            return

        execution = response.execution
        job_id = execution.job_id
        doc = execution.job_document or {}

        logger.info("[%s] Starting OTA job %s: %s", self.robot_id, job_id, doc)

        # IN_PROGRESS に更新
        self._update_job(job_id, iotjobs.JobStatus.IN_PROGRESS)

        # OTA 適用 (速度変更)
        try:
            if self._state:
                new_speed = float(doc.get("max_speed", self._state.max_speed))
                new_version = str(doc.get("version", self._state.firmware_version))
                self._state.apply_ota(new_speed, new_version)
                logger.info(
                    "[%s] OTA applied: speed=%.2f version=%s",
                    self.robot_id,
                    new_speed,
                    new_version,
                )

            # 成功
            self._update_job(job_id, iotjobs.JobStatus.SUCCEEDED)
        except Exception:
            logger.exception("[%s] OTA job %s failed", self.robot_id, job_id)
            self._update_job(job_id, iotjobs.JobStatus.FAILED)

    def _start_next_job(self) -> None:
        self._jobs_client.start_next_pending_job_execution(
            request=iotjobs.StartNextJobExecutionRequest(thing_name=self.robot_id),
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )

    def _update_job(self, job_id: str, status: iotjobs.JobStatus) -> None:
        self._jobs_client.update_job_execution(
            request=iotjobs.UpdateJobExecutionRequest(
                thing_name=self.robot_id,
                job_id=job_id,
                status=status,
            ),
            qos=mqtt.QoS.AT_LEAST_ONCE,
        )

    # ─── 接続イベント ──────────────────────────────────────

    def _on_connection_interrupted(self, connection: Any, error: Any, **kwargs: Any) -> None:
        logger.warning("[%s] Connection interrupted: %s", self.robot_id, error)

    def _on_connection_resumed(self, connection: Any, return_code: Any, session_present: bool, **kwargs: Any) -> None:
        logger.info("[%s] Connection resumed (session_present=%s)", self.robot_id, session_present)
        if not session_present:
            self._subscribe_commands()
