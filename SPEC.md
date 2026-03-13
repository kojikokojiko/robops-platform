# RobOps Platform - 技術仕様書

## 概要

お掃除ロボットの運用管理プラットフォーム。AWS IoT Coreを中核に、複数ロボットのリアルタイム監視・制御・OTAアップデート・スケジューリングを実現する。実物ロボットは用意せず、**ロボットエミュレータを ECS Fargate 上で常時稼働**させてデモを行う。デモ時は5台のエミュレータロボットを扱うが、数万台規模へのスケールを前提としたアーキテクチャとする。

---

## システムアーキテクチャ

### ローカル開発環境

> **全 AWS サービスは dev 環境の実リソースに接続する（LocalStack は使わない）。**
> アプリコード（エミュレータ・バックエンド・フロントエンド）だけローカルで動かす。
> Terraform で dev / prod を別リソースとして管理するため、本番への影響はゼロ。

```
  開発者のPC
  ┌─────────────────────────────────────────────────────────────┐
  │                                                               │
  │  Docker Compose (エミュレータ)                                │
  │  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
  │  │ robot-001  │  │ robot-002  │  │ robot-003  │  ...        │
  │  │ (Python)   │  │ (Python)   │  │ (Python)   │             │
  │  │ certs: vol │  │ certs: vol │  │ certs: vol │             │
  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘             │
  │        └───────────────┴───────────────┘                     │
  │                        │ MQTT/TLS                             │
  │                        │                                      │
  │  FastAPI (uvicorn :8000)           Vite dev server (:5173)   │
  │  ┌───────────────────────┐         ┌─────────────────────┐   │
  │  │  ・ロボット管理 API    │◄────────│  React Dashboard    │   │
  │  │  ・コマンド送信        │  HTTP   │  (HTTP + WebSocket) │   │
  │  │  ・テレメトリ取得      │  /WS    └─────────────────────┘   │
  │  │  ・スケジュール管理    │                                    │
  │  │  ・OTA 管理           │                                    │
  │  └──────────┬────────────┘                                   │
  │             │ boto3 / AWS SDK  (AWS_PROFILE=dev)              │
  └─────────────┼───────────────────────────────────────────────┘
                │ すべて実 AWS dev リソースに接続
                ↓
┌─────────────────────────────────────────────────────────────────┐
│  AWS CLOUD  ── dev 環境  (Terraform workspace: dev)             │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  AWS IoT Core (dev)                                       │  │
│  │  MQTT Broker  ・IoT Registry  ・IoT Rules  ・IoT Jobs     │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│               ┌─────────────┴─────────────┐                     │
│               ↓                           ↓                     │
│  ┌────────────────────┐     ┌─────────────────────────────┐     │
│  │  DynamoDB (dev)    │     │  Timestream (dev)           │     │
│  │  ロボット状態       │     │  テレメトリ時系列データ       │     │
│  └────────────────────┘     └─────────────────────────────┘     │
│                                                                   │
│  ┌──────────────────────┐   ┌──────────────┐  ┌─────────────┐  │
│  │  EventBridge (dev)   │   │   S3 (dev)   │  │  ECR (dev)  │  │
│  └──────────────────────┘   └──────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘

※ ローカルと本番 (prod) の差分
  ローカル                         本番 (AWS prod)
  ──────────────────────────────────────────────────────
  uvicorn (FastAPI 直起動)    →    Lambda + API Gateway
  Vite dev server             →    S3 + CloudFront
  Docker Compose (emulator)   →    ECS Fargate
  certs: volume mount         →    Secrets Manager
  Cognito: スキップ可          →    Cognito JWT 認証必須
  AWS_PROFILE=dev             →    Lambda IAM Role (prod)
```

---

### AWS 構成 (デモ / 本番環境)

```
  ブラウザ
  ┌──────────────────────┐
  │  Dashboard           │
  │  (React + Vite)      │
  └──────────┬───────────┘
             │ HTTPS / WSS
             ↓
┌────────────────────────────────────────────────────────────────┐
│                         AWS CLOUD                               │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  S3 + CloudFront          Cognito                         │ │
│  │  ダッシュボード配信         ユーザー認証                     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────┐                        │
│  │  API Gateway                         │                        │
│  │  ┌──────────────┐  ┌──────────────┐  │                        │
│  │  │  HTTP API    │  │ WebSocket API│  │                        │
│  │  │  (REST)      │  │ (リアルタイム)│  │                        │
│  │  └──────┬───────┘  └──────┬───────┘  │                        │
│  └─────────┼─────────────────┼──────────┘                        │
│            ↓                 ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Lambda (FastAPI / Mangum)                                │   │
│  │  ・ロボット管理 API                                        │   │
│  │  ・コマンド送信          ──────────────────────────────┐  │   │
│  │  ・テレメトリ取得                                        │  │   │
│  │  ・スケジュール管理                                       │  │   │
│  │  ・OTA 管理                                              │  │   │
│  └──────────────────────────────────────────────────────────┘   │
│       │              │              │              │             │
│       ↓              ↓              ↓              ↓             │
│  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────┐   │
│  │DynamoDB │  │Timestream │  │EventBridge│  │  IoT Jobs     │   │
│  │ロボット  │  │テレメトリ  │  │スケジュール│  │  OTA 配信     │   │
│  │状態管理  │  │時系列データ│  │トリガー   │  │               │   │
│  └─────────┘  └───────────┘  └──────────┘  └───────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  AWS IoT Core                                             │ │
│  │  MQTT Broker  ・IoT Registry  ・IoT Rules  ・Fleet Index  │ │
│  └──────────────────────────────┬────────────────────────────┘ │
│                                  │ MQTT/TLS                      │
│  ┌───────────────────────────────┴───────────────────────────┐ │
│  │  ECS Fargate (Robot Emulators)                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │ │
│  │  │ robot-001  │  │ robot-002  │  │ robot-003  │  ...     │ │
│  │  │ (Python)   │  │ (Python)   │  │ (Python)   │          │ │
│  │  │            │  │            │  │            │          │ │
│  │  │ 証明書:     │  │ 証明書:     │  │ 証明書:     │          │ │
│  │  │ Secrets Mgr│  │ Secrets Mgr│  │ Secrets Mgr│          │ │
│  │  └────────────┘  └────────────┘  └────────────┘          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  ECR  (Dockerイメージ保存)   Secrets Manager (IoT証明書)  │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

---

## ディレクトリ構成

```
robops_platform/
├── SPEC.md                          # 本仕様書
├── README.md
├── .github/
│   └── workflows/
│       ├── ci.yml                   # CI (lint + test)
│       ├── deploy-frontend.yml      # フロントエンドデプロイ
│       └── deploy-backend.yml       # バックエンドデプロイ
│
├── infrastructure/                  # Terraform
│   ├── environments/
│   │   ├── dev/
│   │   └── prod/
│   └── modules/
│       ├── iot_core/
│       ├── dynamodb/
│       ├── timestream/
│       ├── lambda/
│       ├── api_gateway/
│       ├── eventbridge/
│       ├── s3_cloudfront/
│       ├── cognito/
│       └── ecs_emulator/            # ECS Fargate ロボットエミュレータ
│
├── backend/                         # Python FastAPI
│   ├── app/
│   │   ├── main.py                  # FastAPI エントリポイント
│   │   ├── api/
│   │   │   ├── robots.py            # ロボット管理API
│   │   │   ├── commands.py          # コマンド送信API
│   │   │   ├── telemetry.py         # テレメトリAPI
│   │   │   ├── schedules.py         # スケジュールAPI
│   │   │   └── ota.py               # OTA管理API
│   │   ├── models/
│   │   │   ├── robot.py
│   │   │   └── telemetry.py
│   │   ├── services/
│   │   │   ├── iot_service.py       # AWS IoT Core操作
│   │   │   ├── dynamodb_service.py
│   │   │   ├── timestream_service.py
│   │   │   └── scheduler_service.py
│   │   └── websocket/
│   │       └── handler.py           # WebSocket Lambda
│   ├── lambda_handlers/
│   │   ├── telemetry_processor.py   # IoT Rule → DynamoDB/Timestream
│   │   ├── websocket_broadcaster.py # DynamoDB Stream → WebSocket
│   │   └── scheduler_trigger.py    # EventBridge → IoT command
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
│
├── emulator/                        # ロボットエミュレータ
│   ├── docker-compose.yml
│   ├── robot/
│   │   ├── Dockerfile
│   │   ├── main.py                  # ロボットエミュレータ本体
│   │   ├── robot_state.py           # ロボット状態機械
│   │   ├── mqtt_client.py           # AWS IoT MQTT接続
│   │   └── config.py
│   ├── certs/                       # IoT証明書 (git-ignored)
│   └── README.md
│
└── frontend/                        # React + Vite
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── components/
    │   │   ├── FleetMap/             # フロアマップ + ロボット位置
    │   │   ├── RobotCard/            # 個別ロボット情報カード
    │   │   ├── TelemetryChart/       # バッテリー・速度グラフ
    │   │   ├── CommandPanel/         # コマンド送信UI
    │   │   ├── ScheduleManager/      # スケジュール管理
    │   │   └── OTAManager/           # OTAアップデートUI
    │   ├── hooks/
    │   │   ├── useRobots.ts
    │   │   ├── useWebSocket.ts
    │   │   └── useTelemetry.ts
    │   ├── api/
    │   │   └── client.ts             # APIクライアント
    │   └── types/
    │       └── robot.ts
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    └── .eslintrc.json
```

---

## MQTTトピック設計

| トピック | 方向 | 説明 |
|---------|------|------|
| `robots/{robot_id}/telemetry` | Robot → Cloud | バッテリー・位置・速度・状態を定期送信 |
| `robots/{robot_id}/status` | Robot → Cloud | 接続状態 (online/offline) |
| `robots/{robot_id}/commands` | Cloud → Robot | コマンド送信 |
| `$aws/things/{robot_id}/jobs/notify` | Cloud → Robot | IoT Jobs通知 (OTA) |
| `$aws/things/{robot_id}/jobs/+/get` | Robot ↔ Cloud | OTAジョブ詳細取得 |
| `$aws/things/{robot_id}/jobs/+/update` | Robot → Cloud | OTAジョブ進捗更新 |

### テレメトリペイロード例
```json
{
  "robot_id": "robot-001",
  "timestamp": "2024-01-01T00:00:00Z",
  "battery_level": 85.5,
  "position": {"x": 3.2, "y": 1.8, "room": "living_room"},
  "speed": 0.5,
  "status": "CLEANING",
  "error_code": null
}
```

### コマンドペイロード例
```json
{
  "command": "START_CLEANING",
  "params": {"room_id": "living_room"},
  "issued_by": "dashboard",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## ロボット状態機械

```
         ┌──────────────────┐
         │      IDLE        │◄──────────────┐
         └────────┬─────────┘               │
                  │ START_CLEANING           │ STOP / 掃除完了
                  ▼                          │
         ┌──────────────────┐               │
         │    CLEANING      ├───────────────┘
         └──┬────────────┬──┘
            │            │
  battery<20%│            │RETURN_TO_DOCK コマンド
            ▼            ▼
   ┌──────────────┐  ┌───────────────────┐
   │ LOW_BATTERY  │  │ RETURNING_TO_DOCK │
   └──────┬───────┘  └─────────┬─────────┘
          │                    │
          └──────┬─────────────┘
                 │ ドック到達
                 ▼
         ┌──────────────────┐
         │    CHARGING      │
         └──────────────────┘
                 │ battery=100%
                 ▼
         ┌──────────────────┐
         │      IDLE        │

※ UPDATING: OTA実行中（いつでも遷移可能）
※ ERROR: 異常検知時
```

---

## AWS IoT スケーラビリティ設計

### なぜこの構成で大規模対応できるか

| 要素 | スケール設計 |
|------|------------|
| AWS IoT Core | フルマネージド。数百万デバイスに対応。追加設定不要 |
| DynamoDB | On-Demand Capacity。書き込み/読み込みが自動スケール |
| Timestream | サーバーレス時系列DB。IoTテレメトリに最適化 |
| Lambda | 同時実行数を自動スケール（デフォルト上限1000→申請で拡張可） |
| API Gateway | 完全マネージド。秒間数万リクエスト対応 |
| IoT Fleet Indexing | フリート横断クエリ（"battery < 20% のロボット全台"等） |
| IoT Jobs | 大規模デバイスへのOTA一括配信。ロールアウト戦略設定可 |

### DynamoDBテーブル設計

**robots テーブル**
```
PK: robot_id (String)
SK: -
Attributes: name, status, battery_level, position, speed,
            firmware_version, last_seen, room_assignment
GSI: status-index (status → robot_id でフリートフィルタ)
```

**schedules テーブル**
```
PK: schedule_id (String)
SK: robot_id (String)
Attributes: cron_expression, room_id, enabled,
            eventbridge_rule_name, created_at
```

**ota_jobs テーブル**
```
PK: job_id (String)
SK: robot_id (String)
Attributes: firmware_version, status, progress, started_at, completed_at
```

---

## API エンドポイント設計

### REST API (HTTP API Gateway)

| Method | Path | 説明 |
|--------|------|------|
| GET | /robots | ロボット一覧取得 |
| GET | /robots/{robot_id} | ロボット詳細取得 |
| POST | /robots/{robot_id}/commands | コマンド送信 |
| GET | /robots/{robot_id}/telemetry | テレメトリ履歴取得 |
| GET | /schedules | スケジュール一覧 |
| POST | /schedules | スケジュール作成 |
| DELETE | /schedules/{schedule_id} | スケジュール削除 |
| GET | /ota/jobs | OTAジョブ一覧 |
| POST | /ota/jobs | OTAジョブ作成（速度変更ファームウェア） |
| GET | /ota/jobs/{job_id} | OTAジョブ状態取得 |

### WebSocket API (リアルタイム通知)

| Action | 説明 |
|--------|------|
| `connect` | 接続時: 全ロボット現在状態を送信 |
| `subscribe_robot` | 特定ロボットのリアルタイム更新を購読 |
| `telemetry_update` | テレメトリ更新通知 (Server→Client) |
| `status_change` | ロボット状態変化通知 (Server→Client) |
| `alert` | 低バッテリーアラート通知 (Server→Client) |

---

## OTA (ファームウェア更新) 設計

デモでは「移動速度の変更」をファームウェアアップデートとして扱う。

### フロー
1. ダッシュボードから「OTA実行」ボタン押下（対象ロボット選択、新速度指定）
2. バックエンドが S3 に「ファームウェアマニフェスト」をアップロード
3. AWS IoT Jobs でジョブを作成し、対象ロボットに配信
4. エミュレータロボットが IoT Jobs 通知を受信
5. マニフェストに従って移動速度を更新
6. ジョブ進捗を IoT Jobs API で更新 (IN_PROGRESS → SUCCEEDED)
7. ダッシュボードでリアルタイム進捗確認

### OTAマニフェスト例
```json
{
  "version": "1.2.0",
  "changes": {
    "max_speed": 0.8,
    "description": "速度を 0.5 → 0.8 m/s に更新"
  }
}
```

---

## スケジュール設計

- EventBridge Scheduler でcron式を登録
- 指定時刻に Lambda をトリガー
- Lambda が対象ロボットに START_CLEANING コマンドを送信

---

## フロントエンド画面設計

### 1. フリートダッシュボード (メイン画面)
- フロアマップ上に全ロボットの現在位置をリアルタイム表示
- 各ロボットのステータスバッジ (色分け)
- バッテリー残量の一覧
- アクティブアラート表示

### 2. ロボット詳細画面
- デジタルツイン表示 (状態・位置・速度・バッテリー)
- バッテリー推移グラフ (過去1時間)
- 走行速度グラフ (過去1時間)
- コマンドパネル (掃除開始/停止/充電ドックへ戻す/部屋指定)

### 3. スケジュール管理画面
- スケジュール一覧
- 新規スケジュール作成 (ロボット選択・部屋選択・日時設定)
- 有効/無効切り替え

### 4. OTA管理画面
- ロボット別ファームウェアバージョン一覧
- OTAジョブ作成 (対象ロボット選択・新速度指定)
- ジョブ進捗一覧 (リアルタイム更新)

---

## CI/CD 設計

### GitHub Actions ワークフロー

**CI (全ブランチ・PR)**
- Python: `uv run ruff check` (lint) + `uv run pytest` (unit tests)
- TypeScript: ESLint + Vitest
- Terraform: fmt check + validate + tflint

**CD (mainブランチマージ時)**
- Backend: `uv export` で requirements.txt 生成 → Lambda ZIP → S3アップロード → Lambda更新
- Frontend: `npm run build` → S3アップロード → CloudFrontキャッシュ無効化
- Infrastructure: `terraform apply` (planをCIで確認済み)

**Python 環境管理ルール**
- `pip` は使わない。すべて `uv` で統一
- ローカル開発: `uv sync` で仮想環境セットアップ
- スクリプト実行: `uv run python ...` または `uv run pytest`
- 依存追加: `uv add <package>` / dev依存: `uv add --dev <package>`
- Lambda デプロイ用: `uv export --no-dev -o requirements.txt`

---

## ロボットエミュレータ設計

### 動作概要
- 各エミュレータはAWS IoT Coreに接続 (TLS証明書認証)
- 1秒ごとにテレメトリを送信
- コマンドトピックを購読し、受信時に状態遷移
- バッテリーは時間経過で減少 (掃除中は速く、充電中は増加)
- 部屋内をランダムに移動する位置シミュレーション

### 実行環境

| 環境 | 動かし方 | 用途 |
|------|---------|------|
| ローカル開発 | `docker-compose up` | 開発・デバッグ |
| AWS (デモ/本番) | ECS Fargate | 常時稼働デモ |

同一のDockerイメージを両環境で使用する。証明書はローカルではボリュームマウント、ECS では AWS Secrets Manager から取得。

### Docker Compose 構成 (ローカル開発用)
```yaml
services:
  robot-001:
    image: robops/robot-emulator
    environment:
      ROBOT_ID: robot-001
      AWS_IOT_ENDPOINT: xxx.iot.ap-northeast-1.amazonaws.com
      CERT_SOURCE: volume   # ローカルはボリューム
    volumes:
      - ./certs/robot-001:/certs
  robot-002:
    ...
```

### ECS Fargate 構成 (デモ/本番環境)
- ECR にDockerイメージをプッシュ
- ECS タスク定義: robot-001〜robot-005 それぞれ独立したタスク
- 証明書は **AWS Secrets Manager** に格納し、タスク起動時に環境変数として注入
- ECS Service で常時1タスク稼働 (障害時は自動再起動)
- スケールアウト時は ECS タスク数を増やすだけ

```
Secrets Manager
  └── /robops/certs/robot-001/ca      → ECS env: IOT_CA_CERT
  └── /robops/certs/robot-001/cert    → ECS env: IOT_CERT
  └── /robops/certs/robot-001/key     → ECS env: IOT_PRIVATE_KEY
```

---

## セキュリティ設計

| 要素 | 対策 |
|------|------|
| ロボット認証 | X.509証明書 (IoT Thing Certificate) |
| IoTポリシー | 各ロボットは自分のトピックのみ pub/sub 可 |
| API認証 | Cognito JWT (ダッシュボードログイン) |
| 証明書管理 (ローカル) | `emulator/certs/` に配置 (git-ignored) |
| 証明書管理 (ECS) | AWS Secrets Manager に格納、タスク起動時に注入 |
| 通信暗号化 | MQTT over TLS 1.2、HTTPS のみ |

---

## 実装ステップ

### Phase 1: 基盤構築 (Step 1-3)
1. **プロジェクト初期化** - ディレクトリ構造、git、CI/CD設定、Linting
2. **Terraform基盤** - IoT Core、DynamoDB、Timestream、Lambda、API Gateway
3. **ロボットエミュレータ** - Docker Compose + Python MQTT クライアント

### Phase 2: バックエンド (Step 4-5)
4. **FastAPI バックエンド** - Lambda関数、REST API、IoT連携
5. **Lambda IoT処理** - テレメトリ処理、WebSocket通知、スケジューラー

### Phase 3: フロントエンド (Step 6-7)
6. **Reactダッシュボード基盤** - フリートマップ、ロボットカード、リアルタイム
7. **高度UI** - グラフ、スケジュール管理、OTA管理

### Phase 4: 統合・完成 (Step 8)
8. **E2E統合テスト** - エミュレータ↔IoT↔API↔ダッシュボード動作確認

---

## 使用技術スタック一覧

| カテゴリ | 技術 |
|---------|------|
| フロントエンド | React 18, Vite, TypeScript, TanStack Query, Recharts, Tailwind CSS |
| バックエンド | Python 3.12, FastAPI, Mangum, Pydantic v2, boto3 |
| **Python パッケージ管理** | **uv** (仮想環境・依存関係管理・スクリプト実行すべて uv で統一) |
| IoT | AWS IoT Core, MQTT (paho-mqtt / AWSIoTPythonSDK v2), AWS IoT Jobs |
| データベース | DynamoDB (状態管理), Amazon Timestream (時系列) |
| インフラ | Terraform 1.7+, AWS Lambda, API Gateway v2, EventBridge, S3, CloudFront, Cognito, ECS Fargate, ECR, Secrets Manager |
| CI/CD | GitHub Actions, Ruff, ESLint, pytest, Vitest, tflint |
| エミュレータ | Docker Compose (ローカル), ECS Fargate (AWS), Python |

---

*作成日: 2024年*
*バージョン: 1.0*
