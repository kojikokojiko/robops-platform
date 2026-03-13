"""
エミュレータ設定ローダー。
ローカル (CERT_SOURCE=volume) と ECS (CERT_SOURCE=secrets_manager) の両方に対応。
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class RobotConfig:
    robot_id: str
    iot_endpoint: str
    region: str

    # 証明書パス (実際のファイルパス。secrets_manager の場合は一時ファイルに書き出す)
    cert_path: str
    key_path: str
    ca_path: str

    # テレメトリ送信間隔 (秒)
    telemetry_interval: float = 1.0

    # バッテリー関連
    battery_drain_rate: float = 0.05  # % / tick (掃除中)
    battery_charge_rate: float = 0.2  # % / tick (充電中)
    low_battery_threshold: float = 20.0  # %

    # ローカル開発時の初期バッテリー (ランダムにしてロボットごとに差を出す)
    initial_battery: float = field(default_factory=lambda: 80.0)

    # 一時ファイル (secrets_manager 使用時にクリーンアップ対象)
    _temp_dir: tempfile.TemporaryDirectory | None = field(default=None, repr=False)

    def cleanup(self) -> None:
        """一時ファイルを削除 (secrets_manager 使用時のみ)"""
        if self._temp_dir is not None:
            self._temp_dir.cleanup()


def load_config() -> RobotConfig:
    """環境変数から設定を読み込む"""
    robot_id = _require("ROBOT_ID")
    iot_endpoint = _require("IOT_ENDPOINT")
    region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
    cert_source = os.getenv("CERT_SOURCE", "volume")

    if cert_source == "secrets_manager":
        cert_path, key_path, ca_path, tmp_dir = _load_from_secrets_manager(robot_id)
    else:
        cert_path, key_path, ca_path = _load_from_volume(robot_id)
        tmp_dir = None

    # バッテリー初期値: ロボットごとに差を出す (robot_id の末尾数字を利用)
    suffix = robot_id.split("-")[-1]
    initial_battery = 60.0 + (int(suffix) % 5) * 8.0  # 60~92%

    return RobotConfig(
        robot_id=robot_id,
        iot_endpoint=iot_endpoint,
        region=region,
        cert_path=cert_path,
        key_path=key_path,
        ca_path=ca_path,
        initial_battery=initial_battery,
        _temp_dir=tmp_dir,
    )


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set")
    return value


def _load_from_volume(robot_id: str) -> tuple[str, str, str]:
    """
    ローカル開発用: emulator/certs/<robot_id>/ からファイルを読み込む。
    期待するファイル:
      - certificate.pem.crt
      - private.pem.key
      - AmazonRootCA1.pem
    """
    cert_dir = Path(os.getenv("CERT_DIR", "/certs"))
    cert_path = str(cert_dir / "certificate.pem.crt")
    key_path = str(cert_dir / "private.pem.key")
    ca_path = str(cert_dir / "AmazonRootCA1.pem")

    for path in [cert_path, key_path, ca_path]:
        if not Path(path).exists():
            raise FileNotFoundError(
                f"Certificate file not found: {path}\n"
                f"Run 'scripts/create_certs.sh' or place certificates in {cert_dir}"
            )

    return cert_path, key_path, ca_path


def _load_from_secrets_manager(robot_id: str) -> tuple[str, str, str, tempfile.TemporaryDirectory]:
    """
    ECS 用: Secrets Manager から証明書を取得して一時ファイルに書き出す。
    Secret の構造:
      {
        "certificate_pem": "...",
        "private_key": "...",
        "ca_url": "https://..."
      }
    """
    import urllib.request

    import boto3

    secret_name = _require("SECRET_NAME")
    region = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])

    tmp_dir = tempfile.TemporaryDirectory(prefix=f"robops-{robot_id}-")
    tmp_path = Path(tmp_dir.name)

    # 証明書ファイルを一時ディレクトリに書き出す
    cert_path = str(tmp_path / "certificate.pem.crt")
    key_path = str(tmp_path / "private.pem.key")
    ca_path = str(tmp_path / "AmazonRootCA1.pem")

    Path(cert_path).write_text(secret["certificate_pem"])
    Path(key_path).write_text(secret["private_key"])

    # CA 証明書はパブリックなので URL からダウンロード
    ca_url = secret.get("ca_url", "https://www.amazontrust.com/repository/AmazonRootCA1.pem")
    with urllib.request.urlopen(ca_url) as resp:  # noqa: S310
        Path(ca_path).write_bytes(resp.read())

    return cert_path, key_path, ca_path, tmp_dir
