"""
ロボットエミュレータのエントリポイント。
"""

from __future__ import annotations

import logging
import signal
import sys

from .config import load_config
from .mqtt_client import RobotMqttClient
from .robot_state import RobotState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    logger.info("Starting robot emulator: %s", config.robot_id)

    state = RobotState(
        robot_id=config.robot_id,
        battery_level=config.initial_battery,
        battery_drain_rate=config.battery_drain_rate,
        battery_charge_rate=config.battery_charge_rate,
        low_battery_threshold=config.low_battery_threshold,
    )

    client = RobotMqttClient(
        robot_id=config.robot_id,
        iot_endpoint=config.iot_endpoint,
        cert_path=config.cert_path,
        key_path=config.key_path,
        ca_path=config.ca_path,
        telemetry_interval=config.telemetry_interval,
    )

    # SIGTERM / SIGINT でクリーンシャットダウン
    def shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down robot %s ...", config.robot_id)
        client.disconnect()
        config.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        client.connect(state)
        client.run_forever()
    except Exception:
        logger.exception("Fatal error in robot %s", config.robot_id)
        raise
    finally:
        config.cleanup()


if __name__ == "__main__":
    main()
