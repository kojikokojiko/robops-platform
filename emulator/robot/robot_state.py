"""
ロボット状態機械。MQTT に依存しない純粋なロジック。

状態遷移:
  IDLE → (START_CLEANING) → CLEANING
  CLEANING → (STOP / 掃除完了) → IDLE
  CLEANING → (battery < threshold) → LOW_BATTERY
  CLEANING / IDLE → (RETURN_TO_DOCK) → RETURNING_TO_DOCK
  LOW_BATTERY → (RETURN_TO_DOCK / 自動) → RETURNING_TO_DOCK
  RETURNING_TO_DOCK → (ドック到達) → CHARGING
  CHARGING → (battery == 100%) → IDLE
  * → (OTA開始) → UPDATING
  UPDATING → (完了) → IDLE
  * → (異常) → ERROR
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RobotStatus(str, Enum):  # noqa: UP042
    IDLE = "IDLE"
    CLEANING = "CLEANING"
    CHARGING = "CHARGING"
    RETURNING_TO_DOCK = "RETURNING_TO_DOCK"
    LOW_BATTERY = "LOW_BATTERY"
    UPDATING = "UPDATING"
    ERROR = "ERROR"


@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0
    room: str = "charging_dock"

    def distance_to(self, other: Position) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def to_dict(self) -> dict[str, Any]:
        return {"x": round(self.x, 2), "y": round(self.y, 2), "room": self.room}


# フロアマップ: 部屋名 → (x_min, y_min, x_max, y_max)
ROOMS: dict[str, tuple[float, float, float, float]] = {
    "living_room": (1.0, 0.0, 6.0, 4.0),
    "kitchen": (6.0, 0.0, 10.0, 4.0),
    "bedroom_1": (0.0, 4.0, 5.0, 8.0),
    "bedroom_2": (5.0, 4.0, 10.0, 8.0),
    "charging_dock": (0.0, 0.0, 1.0, 1.0),
}

DOCK_POSITION = Position(x=0.5, y=0.5, room="charging_dock")


@dataclass
class RobotState:
    robot_id: str
    battery_level: float = 100.0
    status: RobotStatus = RobotStatus.IDLE
    position: Position = field(default_factory=lambda: Position(x=0.5, y=0.5, room="charging_dock"))
    speed: float = 0.0  # m/s
    firmware_version: str = "1.0.0"
    current_room: str | None = None  # 掃除中の部屋
    error_code: str | None = None

    # 内部状態
    _last_tick: float = field(default_factory=time.time, repr=False)
    _target_position: Position | None = field(default=None, repr=False)
    _cleaning_progress: float = field(default=0.0, repr=False)  # 0-100%

    # 設定
    battery_drain_rate: float = 0.05   # % / tick
    battery_charge_rate: float = 0.2   # % / tick
    low_battery_threshold: float = 20.0
    max_speed: float = 0.5  # m/s (OTA で変更される)

    def handle_command(self, command: str, params: dict[str, Any] | None = None) -> bool:
        """
        コマンドを受け取り状態を遷移させる。
        Returns: コマンドが受理されたか
        """
        params = params or {}

        if command == "START_CLEANING":
            return self._cmd_start_cleaning(params.get("room_id"))
        elif command == "STOP_CLEANING":
            return self._cmd_stop_cleaning()
        elif command == "RETURN_TO_DOCK":
            return self._cmd_return_to_dock()
        elif command == "SET_SPEED":
            return self._cmd_set_speed(float(params.get("speed", self.max_speed)))
        else:
            return False

    def apply_ota(self, new_speed: float, new_version: str) -> None:
        """OTA アップデートを適用する (速度変更 = ファームウェア更新のデモ)"""
        prev_status = self.status
        self.status = RobotStatus.UPDATING
        self.speed = 0.0

        # OTA 適用
        self.max_speed = new_speed
        self.firmware_version = new_version

        # 掃除中だった場合は再開、それ以外は IDLE に戻る
        if prev_status == RobotStatus.CLEANING:
            self.status = RobotStatus.CLEANING
            self.speed = self.max_speed
        else:
            self.status = RobotStatus.IDLE

    def tick(self) -> None:
        """
        時間経過による状態更新。1秒ごとに呼ばれることを想定。
        バッテリー・位置・自動遷移を処理する。
        """
        now = time.time()
        elapsed = now - self._last_tick
        self._last_tick = now

        if self.status == RobotStatus.CLEANING:
            self._tick_cleaning(elapsed)
        elif self.status == RobotStatus.CHARGING:
            self._tick_charging(elapsed)
        elif self.status == RobotStatus.RETURNING_TO_DOCK:
            self._tick_returning(elapsed)
        elif self.status == RobotStatus.LOW_BATTERY:
            # 低バッテリーでは自動的にドックへ戻る
            self._cmd_return_to_dock()

    def to_telemetry(self) -> dict[str, Any]:
        """MQTT に送信するテレメトリペイロードを生成"""
        return {
            "robot_id": self.robot_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "battery_level": round(self.battery_level, 1),
            "position": self.position.to_dict(),
            "speed": round(self.speed, 2),
            "status": self.status.value,
            "firmware_version": self.firmware_version,
            "error_code": self.error_code,
        }

    # ─── 内部コマンドハンドラ ──────────────────────────────

    def _cmd_start_cleaning(self, room_id: str | None) -> bool:
        if self.status not in (RobotStatus.IDLE,):
            return False
        if self.battery_level <= self.low_battery_threshold:
            return False

        room = room_id if room_id in ROOMS else _random_room()
        self.current_room = room
        self.status = RobotStatus.CLEANING
        self.speed = self.max_speed
        self._cleaning_progress = 0.0
        self._target_position = _random_position_in_room(room)
        return True

    def _cmd_stop_cleaning(self) -> bool:
        if self.status != RobotStatus.CLEANING:
            return False
        self.status = RobotStatus.IDLE
        self.speed = 0.0
        self.current_room = None
        return True

    def _cmd_return_to_dock(self) -> bool:
        if self.status in (RobotStatus.CHARGING, RobotStatus.RETURNING_TO_DOCK):
            return False
        self.status = RobotStatus.RETURNING_TO_DOCK
        self.speed = self.max_speed * 0.8
        self._target_position = DOCK_POSITION
        return True

    def _cmd_set_speed(self, speed: float) -> bool:
        self.max_speed = max(0.1, min(2.0, speed))
        if self.status == RobotStatus.CLEANING:
            self.speed = self.max_speed
        return True

    # ─── Tick ヘルパー ─────────────────────────────────────

    def _tick_cleaning(self, elapsed: float) -> None:
        # バッテリー消耗
        self.battery_level = max(0.0, self.battery_level - self.battery_drain_rate * elapsed * 60)

        # 低バッテリー遷移
        if self.battery_level <= self.low_battery_threshold:
            self.status = RobotStatus.LOW_BATTERY
            self.speed = 0.0
            return

        # 位置移動
        if self._target_position:
            self._move_toward(self._target_position, elapsed)
            if self.position.distance_to(self._target_position) < 0.2:
                # 目標地点到達 → 次のランダム地点へ
                room = self.current_room or "living_room"
                self._target_position = _random_position_in_room(room)

        # 掃除進捗 (60秒で1部屋完了)
        self._cleaning_progress = min(100.0, self._cleaning_progress + elapsed / 60.0 * 100.0)
        if self._cleaning_progress >= 100.0:
            self._cmd_stop_cleaning()

    def _tick_charging(self, elapsed: float) -> None:
        self.battery_level = min(100.0, self.battery_level + self.battery_charge_rate * elapsed * 60)
        self.speed = 0.0
        if self.battery_level >= 100.0:
            self.status = RobotStatus.IDLE

    def _tick_returning(self, elapsed: float) -> None:
        # バッテリーも少しずつ消耗
        self.battery_level = max(0.0, self.battery_level - self.battery_drain_rate * 0.5 * elapsed * 60)

        if self._target_position:
            self._move_toward(self._target_position, elapsed)
            if self.position.distance_to(self._target_position) < 0.3:
                # ドック到達
                self.position = Position(x=DOCK_POSITION.x, y=DOCK_POSITION.y, room="charging_dock")
                self.status = RobotStatus.CHARGING
                self.speed = 0.0
                self._target_position = None

    def _move_toward(self, target: Position, elapsed: float) -> None:
        dist = self.position.distance_to(target)
        if dist < 0.01:
            return
        step = min(self.speed * elapsed, dist)
        ratio = step / dist
        self.position.x += (target.x - self.position.x) * ratio
        self.position.y += (target.y - self.position.y) * ratio
        # 現在いる部屋を更新
        self.position.room = _room_at(self.position.x, self.position.y)


def _random_room() -> str:
    return random.choice([r for r in ROOMS if r != "charging_dock"])  # noqa: S311


def _random_position_in_room(room: str) -> Position:
    x0, y0, x1, y1 = ROOMS[room]
    return Position(
        x=random.uniform(x0 + 0.2, x1 - 0.2),  # noqa: S311
        y=random.uniform(y0 + 0.2, y1 - 0.2),  # noqa: S311
        room=room,
    )


def _room_at(x: float, y: float) -> str:
    for name, (x0, y0, x1, y1) in ROOMS.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return name
    return "unknown"
