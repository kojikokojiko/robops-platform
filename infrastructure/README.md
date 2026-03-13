# Infrastructure (Terraform)

## 構成

```
infrastructure/
├── modules/          # 再利用可能なモジュール
│   ├── dynamodb/         - robots / schedules / ota_jobs / ws_connections テーブル
│   ├── timestream/       - テレメトリ時系列DB
│   ├── s3_cloudfront/    - フロントエンド配信 / Lambda artifacts / OTA バケット
│   ├── cognito/          - ユーザー認証
│   ├── iot_core/         - IoT Things / Certificates / Policy / Rules
│   ├── lambda/           - 全 Lambda 関数 + IAM Role
│   ├── api_gateway/      - HTTP API + WebSocket API
│   ├── ecs_emulator/     - ECR / ECS Cluster / Task / Service
│   └── eventbridge/      - Scheduler グループ + IAM Role
└── environments/
    ├── dev/              - 開発環境
    └── prod/             - 本番環境
```

## 初回セットアップ (Terraform state バックエンド)

`terraform init` の前に、state 保存用の S3 バケットと DynamoDB テーブルを作成する必要があります。

```bash
# dev 環境の state バックエンド作成 (1回だけ)
aws s3 mb s3://robops-terraform-state-dev --region ap-northeast-1
aws s3api put-bucket-versioning \
  --bucket robops-terraform-state-dev \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name robops-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-1
```

## dev 環境のデプロイ手順

```bash
cd infrastructure/environments/dev

# 1. tfvars を準備
cp terraform.tfvars.example terraform.tfvars
# IoT エンドポイントを確認して記入:
# aws iot describe-endpoint --endpoint-type iot:Data-ATS --query endpointAddress --output text

# 2. 初期化
terraform init

# 3. プラン確認
terraform plan

# 4. 適用
terraform apply

# 5. 出力を確認 (.env に反映)
terraform output
```

## terraform apply 後の .env 更新

`terraform output` の結果を `.env` に反映してください:

```bash
# .env に追記
VITE_API_URL=$(terraform output -raw http_api_endpoint)
VITE_WS_URL=$(terraform output -raw websocket_api_endpoint | sed 's/https/wss/')
VITE_COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
VITE_COGNITO_CLIENT_ID=$(terraform output -raw cognito_client_id)
```

## モジュール間の依存関係

```
s3_cloudfront ─────────────────────────────┐
dynamodb ──────────────────────────────────┤
timestream ────────────────────────────────┤──→ lambda ──→ api_gateway
cognito ───────────────────────────────────┘                    │
                                                                 ↓
lambda ──────────────────────────────────────────→ iot_core (IoT Rules)
lambda ──────────────────────────────────────────→ eventbridge
iot_core (Secrets Manager) ──────────────────────→ ecs_emulator
```

## よく使うコマンド

```bash
# 特定リソースのみ更新
terraform apply -target=module.lambda

# 状態確認
terraform state list

# リソース削除 (dev のみ)
terraform destroy
```

## 注意事項

- `terraform.tfvars` は `.gitignore` 済み。コミットしないこと。
- IoT 証明書の秘密鍵は Terraform state に含まれる。state バケットのアクセス制御を適切に設定すること。
- Lambda のコードは GitHub Actions が S3 経由で更新する。`terraform apply` は Lambda コードを上書きしない (`lifecycle.ignore_changes` 設定済み)。
