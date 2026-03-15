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

# バウストロフェドンのストリップ幅 (ロボット直径 ≈ 0.3m、少し重ねる)
STRIP_WIDTH = 0.35
MARGIN = 0.25  # 壁からのマージン
ARRIVAL_THRESHOLD = 0.15  # この距離以下で「到達」とみなす


def _boustrophedon_path(room: str) -> list[Position]:
    """
    指定部屋のバウストロフェドン（ジグザグ往復）経路を生成する。
    Y 方向にストリップを並べ、X 方向を交互に往復する。
    """
    x0, y0, x1, y1 = ROOMS[room]
    xmin, xmax = x0 + MARGIN, x1 - MARGIN
    ymin, ymax = y0 + MARGIN, y1 - MARGIN

    waypoints: list[Position] = []

    y = ymin
    left_to_right = True
    while y <= ymax + 1e-6:
        y_clamped = min(y, ymax)
        if left_to_right:
            waypoints.append(Position(x=xmin, y=y_clamped, room=room))
            waypoints.append(Position(x=xmax, y=y_clamped, room=room))
        else:
            waypoints.append(Position(x=xmax, y=y_clamped, room=room))
            waypoints.append(Position(x=xmin, y=y_clamped, room=room))
        left_to_right = not left_to_right
        y += STRIP_WIDTH

    return waypoints


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
    _waypoints: list[Position] = field(default_factory=list, repr=False)
    _waypoint_index: int = field(default=0, repr=False)
    _cleaning_progress: float = field(default=0.0, repr=False)  # 0-100%

    # 設定
    battery_drain_rate: float = 0.0084  # % / s → 1部屋掃除で約50%消費
    battery_charge_rate: float = 0.083  # % / s → 約10分でフル充電
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

        self.max_speed = new_speed
        self.firmware_version = new_version

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
            "cleaning_progress": round(self._cleaning_progress, 1),
        }

    # ─── 内部コマンドハンドラ ──────────────────────────────

    def _cmd_start_cleaning(self, room_id: str | None) -> bool:
        if self.status not in (RobotStatus.IDLE,):
            return False
        if self.battery_level <= self.low_battery_threshold:
            return False

        room = room_id if room_id in ROOMS and room_id != "charging_dock" else _random_room()
        self.current_room = room
        self.status = RobotStatus.CLEANING
        self.speed = self.max_speed
        self._cleaning_progress = 0.0

        # バウストロフェドン経路を生成
        # 現在位置はそのまま — ロボットが物理的に移動してウェイポイントへ向かう
        self._waypoints = _boustrophedon_path(room)
        self._waypoint_index = 0

        return True

    def _cmd_stop_cleaning(self) -> bool:
        if self.status != RobotStatus.CLEANING:
            return False
        self.status = RobotStatus.IDLE
        self.speed = 0.0
        self.current_room = None
        self._waypoints = []
        self._waypoint_index = 0
        return True

    def _cmd_return_to_dock(self) -> bool:
        if self.status in (RobotStatus.CHARGING, RobotStatus.RETURNING_TO_DOCK):
            return False
        self.status = RobotStatus.RETURNING_TO_DOCK
        self.speed = self.max_speed * 0.8
        self._waypoints = [DOCK_POSITION]
        self._waypoint_index = 0
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

        # ウェイポイントがなければ完了
        if not self._waypoints or self._waypoint_index >= len(self._waypoints):
            self._cmd_stop_cleaning()
            return

        # 現在のウェイポイントに到達するまで移動（同tick内で連続処理）
        remaining = elapsed
        while remaining > 0 and self._waypoint_index < len(self._waypoints):
            target = self._waypoints[self._waypoint_index]
            dist = self.position.distance_to(target)

            if dist < ARRIVAL_THRESHOLD:
                # ウェイポイント到達 → スナップして次へ
                self.position.x = target.x
                self.position.y = target.y
                self.position.room = target.room
                self._waypoint_index += 1
                total = len(self._waypoints)
                self._cleaning_progress = min(100.0, self._waypoint_index / total * 100.0)
                if self._waypoint_index >= total:
                    self._cleaning_progress = 100.0
                    self._cmd_stop_cleaning()
                    return
                # 残り時間で次のウェイポイントへ向かう
                continue

            step = min(self.speed * remaining, dist)
            time_used = step / self.speed if self.speed > 0 else remaining
            self._move_toward(target, time_used)
            remaining -= time_used
            break

    def _tick_charging(self, elapsed: float) -> None:
        self.battery_level = min(
            100.0, self.battery_level + self.battery_charge_rate * elapsed * 60
        )
        self.speed = 0.0
        if self.battery_level >= 100.0:
            self.status = RobotStatus.IDLE

    def _tick_returning(self, elapsed: float) -> None:
        self.battery_level = max(
            0.0, self.battery_level - self.battery_drain_rate * 0.5 * elapsed * 60
        )

        if self._waypoints:
            target = self._waypoints[0]
            self._move_toward(target, elapsed)
            if self.position.distance_to(target) < 0.3:
                self.position = Position(x=DOCK_POSITION.x, y=DOCK_POSITION.y, room="charging_dock")
                self.status = RobotStatus.CHARGING
                self.speed = 0.0
                self._waypoints = []

    def _move_toward(self, target: Position, elapsed: float) -> None:
        dist = self.position.distance_to(target)
        if dist < 0.01:
            return
        step = min(self.speed * elapsed, dist)
        ratio = step / dist
        self.position.x += (target.x - self.position.x) * ratio
        self.position.y += (target.y - self.position.y) * ratio
        self.position.room = _room_at(self.position.x, self.position.y)


def _random_room() -> str:
    import random

    return random.choice([r for r in ROOMS if r != "charging_dock"])  # noqa: S311


def _room_at(x: float, y: float) -> str:
    for name, (x0, y0, x1, y1) in ROOMS.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return name
    return "unknown"
