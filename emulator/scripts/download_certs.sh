#!/usr/bin/env bash
# Terraform で作成された IoT 証明書を Secrets Manager から取得して
# emulator/certs/<robot_id>/ に保存するスクリプト。
#
# 使い方:
#   cd emulator
#   AWS_PROFILE=dev ./scripts/download_certs.sh
#
# 前提:
#   - terraform apply 済み (dev 環境)
#   - AWS CLI がインストール済み
#   - jq がインストール済み

set -euo pipefail

REGION="${AWS_DEFAULT_REGION:-ap-northeast-1}"
ROBOT_IDS=("robot-001" "robot-002" "robot-003" "robot-004" "robot-005")
ENV="${ROBOPS_ENV:-dev}"
PREFIX="robops-${ENV}"

echo "Downloading IoT certificates from Secrets Manager..."
echo "Region: $REGION  Env: $ENV"
echo ""

# AWS Root CA をダウンロード (共通)
CA_URL="https://www.amazontrust.com/repository/AmazonRootCA1.pem"
CA_TMPFILE=$(mktemp)
curl -s "$CA_URL" -o "$CA_TMPFILE"

for ROBOT_ID in "${ROBOT_IDS[@]}"; do
  SECRET_NAME="${PREFIX}/certs/${ROBOT_ID}"
  CERT_DIR="./certs/${ROBOT_ID}"

  echo "  [$ROBOT_ID] Fetching secret: $SECRET_NAME"
  mkdir -p "$CERT_DIR"

  SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" \
    --query SecretString \
    --output text)

  echo "$SECRET_JSON" | jq -r '.certificate_pem' > "${CERT_DIR}/certificate.pem.crt"
  echo "$SECRET_JSON" | jq -r '.private_key'     > "${CERT_DIR}/private.pem.key"
  cp "$CA_TMPFILE"                                  "${CERT_DIR}/AmazonRootCA1.pem"

  chmod 600 "${CERT_DIR}/private.pem.key"
  echo "  [$ROBOT_ID] Saved to $CERT_DIR"
done

rm -f "$CA_TMPFILE"
echo ""
echo "Done. You can now run: docker compose up"
