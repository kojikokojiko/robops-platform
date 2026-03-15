# RobOps Platform

お掃除ロボット運用管理プラットフォーム。AWS IoT Core を中核に、複数ロボットのリアルタイム監視・制御・OTA アップデート・スケジューリングを実現する。

## アーキテクチャ概要

```
[Robot Emulators (Docker / ECS Fargate)]
        ↕ MQTT/TLS
[AWS IoT Core] → IoT Rules → Lambda → DynamoDB
[API Gateway (HTTP + WebSocket)] ↔ Lambda (FastAPI)
[S3 + CloudFront] → React Dashboard (ブラウザ)
```

詳細は [SPEC.md](./SPEC.md) を参照。

---

## ディレクトリ構成

```
robops_platform/
├── backend/        # Python FastAPI (AWS Lambda)
├── emulator/       # ロボットエミュレータ (Docker / ECS Fargate)
├── frontend/       # React + Vite ダッシュボード
├── infrastructure/ # Terraform (AWS リソース)
└── .github/        # CI/CD (GitHub Actions)
```

---

## 必要なツール

| ツール | バージョン | 用途 |
|--------|-----------|------|
| [uv](https://docs.astral.sh/uv/) | latest | Python パッケージ管理 |
| Python | 3.12 | バックエンド・エミュレータ |
| Node.js | 20+ | フロントエンド |
| Docker | latest | エミュレータローカル実行 |
| Terraform | 1.10+ | AWS インフラ管理 |
| AWS CLI | 2.x | AWS 操作 |

---

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repo-url>
cd robops_platform
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して AWS の設定などを記入
```

### 3. Python 環境 (uv)

```bash
# バックエンド
cd backend
uv sync --all-extras

# エミュレータ
cd ../emulator
uv sync --all-extras
```

### 4. フロントエンド

```bash
cd frontend
npm install
```

### 5. pre-commit フックのインストール

```bash
pip install pre-commit
pre-commit install
```

---

## ローカル開発

### バックエンド起動

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

### フロントエンド起動

```bash
cd frontend
npm run dev
# → http://localhost:5173
```

### エミュレータ起動

```bash
cd emulator
# 証明書を emulator/certs/robot-00X/ に配置してから:
docker compose up
```

> **注意**: エミュレータは実際の AWS IoT Core に接続します。
> IoT Thing 証明書の取得方法は [emulator/README.md](./emulator/README.md) を参照。

---

## AWS 環境

### dev 環境のセットアップ (初回のみ)

```bash
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply
```

### AWS プロファイルの設定

`~/.aws/config` に dev プロファイルを追加:

```ini
[profile dev]
region = ap-northeast-1
# SSO や IAM の設定
```

`.env` に以下を設定:

```
AWS_PROFILE=dev
```

---

## CI/CD

| ワークフロー | トリガー | 内容 |
|------------|---------|------|
| `ci.yml` | 全ブランチ push / PR | lint + test + terraform plan |

---

## バックエンドのデプロイ手順（手動）

Lambda へのデプロイは CI/CD を使わず、以下の手順でローカルから行う。

### 1. パッケージビルド

```bash
cd backend
uv export --no-dev -o requirements.txt
pip install -r requirements.txt -t dist/
cp -r app dist/
cp -r lambda_handlers dist/
cd dist && zip -r ../lambda.zip .
```

### 2. S3 にアップロード

```bash
aws s3 cp backend/lambda.zip s3://robops-dev-lambda-artifacts/backend/lambda.zip
```

### 3. Lambda 関数を更新

```bash
for fn in robops-dev-api robops-dev-telemetry-processor robops-dev-ws-broadcaster robops-dev-scheduler-trigger; do
  aws lambda update-function-code \
    --function-name $fn \
    --s3-bucket robops-dev-lambda-artifacts \
    --s3-key backend/lambda.zip \
    --region ap-northeast-1
done
```

> **注意**: `dist/` は `.gitignore` に含まれていること。`lambda.zip` も同様。

---

## 開発コマンド集

```bash
# Python lint
cd backend && uv run ruff check .
cd backend && uv run ruff format .

# Python テスト
cd backend && uv run pytest

# 依存パッケージ追加
cd backend && uv add <package>
cd backend && uv add --dev <package>       # 開発用
cd backend && uv export --no-dev -o requirements.txt  # Lambda デプロイ用

# フロントエンド lint
cd frontend && npm run lint

# フロントエンド テスト
cd frontend && npm test

# Terraform
cd infrastructure/environments/dev
terraform plan
terraform apply
```

---

## 実装フェーズ

| Phase | 内容 | 状態 |
|-------|------|------|
| Step 1 | プロジェクト初期化・CI/CD・Linting | ✅ 完了 |
| Step 2 | Terraform 基盤 (IoT Core, DynamoDB, Lambda, API GW, S3/CloudFront, Cognito, ECS) | ✅ 完了 |
| Step 3 | ロボットエミュレータ (Docker + Python MQTT) | ✅ 完了 |
| Step 4 | FastAPI バックエンド | ✅ 完了 |
| Step 5 | React フロントエンド | ✅ 完了 |
| Step 6 | OTA・スケジューリング | ✅ 完了 (Step 5 と同時実装) |
| Step 7 | 結合テスト | ✅ 完了 |
