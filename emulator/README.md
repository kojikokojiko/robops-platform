# Robot Emulator

お掃除ロボットをエミュレートする Python プロセス。
AWS IoT Core に MQTT/TLS で接続し、テレメトリの送信・コマンド受信・OTA Jobs 処理を行う。

## ローカルでの起動手順

### 1. 証明書の取得

Terraform で作成された IoT 証明書を Secrets Manager からダウンロードする。

```bash
cd emulator
cp .env.example .env
# .env に IOT_ENDPOINT を記入

# terraform apply 済みの dev 環境から証明書を取得
AWS_PROFILE=dev ./scripts/download_certs.sh
```

取得後の構造:
```
emulator/certs/
├── robot-001/
│   ├── certificate.pem.crt
│   ├── private.pem.key
│   └── AmazonRootCA1.pem
├── robot-002/ ...
```

> **注意**: `certs/` は `.gitignore` に含まれています。絶対にコミットしないこと。

### 2. Docker Compose で起動

```bash
cd emulator
docker compose up --build
```

特定のロボットだけ起動:

```bash
docker compose up robot-001 robot-002
```

### 3. ログ確認

```bash
docker compose logs -f robot-001
```

---

## ファイル構成

```
emulator/
├── robot/
│   ├── config.py       - 設定ローダー (volume / secrets_manager 両対応)
│   ├── robot_state.py  - 状態機械 (IDLE/CLEANING/CHARGING 等)
│   ├── mqtt_client.py  - AWS IoT MQTT クライアント
│   └── main.py         - エントリポイント
├── tests/
│   └── test_robot_state.py
├── scripts/
│   └── download_certs.sh  - 証明書取得スクリプト
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## ロボット状態機械

```
IDLE → (START_CLEANING) → CLEANING
CLEANING → (STOP / 掃除完了) → IDLE
CLEANING → (battery < 20%) → LOW_BATTERY → RETURNING_TO_DOCK
CLEANING / IDLE → (RETURN_TO_DOCK) → RETURNING_TO_DOCK → CHARGING
CHARGING → (battery = 100%) → IDLE
* → (OTA) → UPDATING → IDLE
```

---

## MQTT トピック

| トピック | 方向 | 内容 |
|---------|------|------|
| `robots/{id}/telemetry` | Robot → Cloud | バッテリー・位置・速度・状態 (1秒ごと) |
| `robots/{id}/status` | Robot → Cloud | online / offline |
| `robots/{id}/commands` | Cloud → Robot | コマンド JSON |
| `$aws/things/{id}/jobs/notify` | Cloud → Robot | OTA ジョブ通知 |

### コマンド例

```json
{ "command": "START_CLEANING", "params": { "room_id": "living_room" } }
{ "command": "STOP_CLEANING" }
{ "command": "RETURN_TO_DOCK" }
{ "command": "SET_SPEED", "params": { "speed": 1.0 } }
```

---

## テスト実行

```bash
cd emulator
uv sync --all-extras
uv run pytest
```

---

## 環境変数

| 変数 | 必須 | 説明 |
|------|------|------|
| `ROBOT_ID` | ✅ | ロボット ID (例: robot-001) |
| `IOT_ENDPOINT` | ✅ | AWS IoT Core エンドポイント |
| `AWS_DEFAULT_REGION` | - | デフォルト: ap-northeast-1 |
| `CERT_SOURCE` | - | `volume` (ローカル) or `secrets_manager` (ECS) |
| `CERT_DIR` | - | volume 時の証明書ディレクトリ (デフォルト: /certs) |
| `SECRET_NAME` | - | secrets_manager 時のシークレット名 |
| `TELEMETRY_INTERVAL` | - | テレメトリ送信間隔秒数 (デフォルト: 1.0) |
