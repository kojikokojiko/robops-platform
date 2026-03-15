"""RobotState の単体テスト (AWS 接続不要)"""

import time

import pytest

from robot.robot_state import ROOMS, RobotState, RobotStatus


@pytest.fixture()
def robot() -> RobotState:
    return RobotState(
        robot_id="robot-test",
        battery_level=100.0,
        battery_drain_rate=0.05,
        battery_charge_rate=0.2,
        low_battery_threshold=20.0,
    )


# ─── コマンド受理テスト ────────────────────────────────────


class TestStartCleaning:
    def test_idle_to_cleaning(self, robot: RobotState) -> None:
        assert robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        assert robot.status == RobotStatus.CLEANING
        assert robot.current_room == "living_room"
        assert robot.speed > 0

    def test_start_cleaning_invalid_room_uses_random(self, robot: RobotState) -> None:
        assert robot.handle_command("START_CLEANING", {"room_id": "nonexistent_room"})
        assert robot.status == RobotStatus.CLEANING
        assert robot.current_room in ROOMS

    def test_cannot_start_from_cleaning(self, robot: RobotState) -> None:
        robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        assert not robot.handle_command("START_CLEANING", {"room_id": "kitchen"})

    def test_cannot_start_with_low_battery(self, robot: RobotState) -> None:
        robot.battery_level = 15.0
        assert not robot.handle_command("START_CLEANING")


class TestStopCleaning:
    def test_cleaning_to_idle(self, robot: RobotState) -> None:
        robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        assert robot.handle_command("STOP_CLEANING")
        assert robot.status == RobotStatus.IDLE
        assert robot.speed == 0.0
        assert robot.current_room is None

    def test_cannot_stop_when_idle(self, robot: RobotState) -> None:
        assert not robot.handle_command("STOP_CLEANING")


class TestReturnToDock:
    def test_from_cleaning(self, robot: RobotState) -> None:
        robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        assert robot.handle_command("RETURN_TO_DOCK")
        assert robot.status == RobotStatus.RETURNING_TO_DOCK

    def test_from_idle(self, robot: RobotState) -> None:
        assert robot.handle_command("RETURN_TO_DOCK")
        assert robot.status == RobotStatus.RETURNING_TO_DOCK

    def test_noop_when_already_charging(self, robot: RobotState) -> None:
        robot.status = RobotStatus.CHARGING
        assert not robot.handle_command("RETURN_TO_DOCK")

    def test_noop_when_already_returning(self, robot: RobotState) -> None:
        robot.handle_command("RETURN_TO_DOCK")
        assert not robot.handle_command("RETURN_TO_DOCK")


class TestSetSpeed:
    def test_set_valid_speed(self, robot: RobotState) -> None:
        assert robot.handle_command("SET_SPEED", {"speed": 1.2})
        assert robot.max_speed == pytest.approx(1.2)

    def test_speed_clamp_min(self, robot: RobotState) -> None:
        robot.handle_command("SET_SPEED", {"speed": 0.0})
        assert robot.max_speed == pytest.approx(0.1)

    def test_speed_clamp_max(self, robot: RobotState) -> None:
        robot.handle_command("SET_SPEED", {"speed": 99.0})
        assert robot.max_speed == pytest.approx(2.0)

    def test_updates_speed_while_cleaning(self, robot: RobotState) -> None:
        robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        robot.handle_command("SET_SPEED", {"speed": 1.5})
        assert robot.speed == pytest.approx(1.5)


# ─── OTA テスト ─────────────────────────────────────────────


class TestOTA:
    def test_apply_ota_while_idle(self, robot: RobotState) -> None:
        robot.apply_ota(new_speed=1.0, new_version="2.0.0")
        assert robot.max_speed == pytest.approx(1.0)
        assert robot.firmware_version == "2.0.0"
        assert robot.status == RobotStatus.IDLE

    def test_apply_ota_while_cleaning_resumes(self, robot: RobotState) -> None:
        robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        robot.apply_ota(new_speed=0.8, new_version="1.1.0")
        assert robot.status == RobotStatus.CLEANING
        assert robot.speed == pytest.approx(0.8)


# ─── tick テスト ───────────────────────────────────────────


class TestTick:
    def test_battery_drains_while_cleaning(self, robot: RobotState) -> None:
        robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        initial = robot.battery_level
        # _last_tick を強制的に過去にずらして elapsed を作る
        robot._last_tick = time.time() - 10.0
        robot.tick()
        assert robot.battery_level < initial

    def test_battery_charges_while_charging(self, robot: RobotState) -> None:
        robot.battery_level = 50.0
        robot.status = RobotStatus.CHARGING
        robot._last_tick = time.time() - 10.0
        robot.tick()
        assert robot.battery_level > 50.0

    def test_low_battery_triggers_return_to_dock(self, robot: RobotState) -> None:
        robot.handle_command("START_CLEANING", {"room_id": "living_room"})
        robot.battery_level = 19.0
        robot.status = RobotStatus.LOW_BATTERY
        robot._last_tick = time.time() - 1.0
        robot.tick()
        assert robot.status == RobotStatus.RETURNING_TO_DOCK

    def test_battery_full_stops_charging(self, robot: RobotState) -> None:
        robot.battery_level = 99.9
        robot.status = RobotStatus.CHARGING
        robot._last_tick = time.time() - 10.0
        robot.tick()
        assert robot.status == RobotStatus.IDLE


# ─── テレメトリ ─────────────────────────────────────────────


class TestTelemetry:
    def test_telemetry_structure(self, robot: RobotState) -> None:
        telemetry = robot.to_telemetry()
        assert telemetry["robot_id"] == "robot-test"
        assert "timestamp" in telemetry
        assert "battery_level" in telemetry
        assert "position" in telemetry
        assert "x" in telemetry["position"]
        assert "y" in telemetry["position"]
        assert "room" in telemetry["position"]
        assert "speed" in telemetry
        assert "status" in telemetry
        assert "firmware_version" in telemetry

    def test_telemetry_status_is_string(self, robot: RobotState) -> None:
        telemetry = robot.to_telemetry()
        assert isinstance(telemetry["status"], str)
