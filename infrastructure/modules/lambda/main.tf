locals {
  name = "${var.prefix}-${var.env}"

  common_env = {
    ENV                         = var.env
    AWS_DEFAULT_REGION          = var.region
    DYNAMODB_TABLE_ROBOTS       = var.dynamodb_robots_table_name
    DYNAMODB_TABLE_SCHEDULES    = var.dynamodb_schedules_table_name
    DYNAMODB_TABLE_OTA_JOBS     = var.dynamodb_ota_jobs_table_name
    DYNAMODB_TABLE_WS_CONNECTIONS = var.dynamodb_ws_connections_table_name
    TIMESTREAM_DATABASE         = var.timestream_database_name
    TIMESTREAM_TABLE            = var.timestream_table_name
    OTA_FIRMWARE_BUCKET         = var.ota_firmware_bucket_name
  }
}

# ─── プレースホルダー ZIP ────────────────────────────────
# 初回 terraform apply 時に使う。実際のコードは GitHub Actions でデプロイ。

data "archive_file" "placeholder" {
  type        = "zip"
  output_path = "${path.module}/placeholder.zip"

  source {
    content  = "def handler(event, context): return {'statusCode': 200, 'body': 'placeholder'}"
    filename = "handler.py"
  }
}

# ─── IAM Role (Lambda 共通) ──────────────────────────────

resource "aws_iam_role" "lambda" {
  name = "${local.name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "robops-permissions"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
          "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan",
          "dynamodb:BatchGetItem", "dynamodb:BatchWriteItem"
        ]
        Resource = [
          var.dynamodb_robots_table_arn,
          "${var.dynamodb_robots_table_arn}/index/*",
          var.dynamodb_schedules_table_arn,
          "${var.dynamodb_schedules_table_arn}/index/*",
          var.dynamodb_ota_jobs_table_arn,
          "${var.dynamodb_ota_jobs_table_arn}/index/*",
          var.dynamodb_ws_connections_table_arn,
        ]
      },
      {
        Sid    = "Timestream"
        Effect = "Allow"
        Action = [
          "timestream:WriteRecords",
          "timestream:DescribeEndpoints",
          "timestream:Select",
          "timestream:SelectValues",
          "timestream:DescribeTable",
          "timestream:ListTables",
        ]
        Resource = "*"
      },
      {
        Sid    = "IoTCore"
        Effect = "Allow"
        Action = [
          "iot:Publish",
          "iot:DescribeEndpoint",
          "iot:CreateJob",
          "iot:DescribeJob",
          "iot:ListJobs",
          "iot:CancelJob",
          "iot:ListThings",
          "iot:DescribeThing",
          "iot:SearchIndex",
        ]
        Resource = "*"
      },
      {
        Sid    = "EventBridge"
        Effect = "Allow"
        Action = [
          "scheduler:CreateSchedule",
          "scheduler:DeleteSchedule",
          "scheduler:ListSchedules",
          "scheduler:GetSchedule",
          "scheduler:UpdateSchedule",
          "iam:PassRole",
        ]
        Resource = "*"
      },
      {
        Sid    = "S3OTA"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          var.ota_firmware_bucket_arn,
          "${var.ota_firmware_bucket_arn}/*",
        ]
      },
      {
        Sid    = "ApiGatewayManage"
        Effect = "Allow"
        Action = ["execute-api:ManageConnections"]
        Resource = "arn:aws:execute-api:*:*:*/@connections/*"
      },
    ]
  })
}

# ─── Lambda: メイン API ──────────────────────────────────

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.name}-api"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name}-api"
  role          = aws_iam_role.lambda.arn
  handler       = "app.main.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  # 初回は placeholder。以降は GitHub Actions が S3 経由で更新
  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.api]
  tags       = var.tags

  lifecycle {
    # GitHub Actions によるコード更新を Terraform が上書きしないよう ignore
    ignore_changes = [filename, source_code_hash, s3_bucket, s3_key]
  }
}

# ─── Lambda: テレメトリ処理 ──────────────────────────────

resource "aws_cloudwatch_log_group" "telemetry_processor" {
  name              = "/aws/lambda/${local.name}-telemetry-processor"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_lambda_function" "telemetry_processor" {
  function_name = "${local.name}-telemetry-processor"
  role          = aws_iam_role.lambda.arn
  handler       = "lambda_handlers.telemetry_processor.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.telemetry_processor]
  tags       = var.tags

  lifecycle {
    ignore_changes = [filename, source_code_hash, s3_bucket, s3_key]
  }
}

# ─── Lambda: WebSocket ─────────────────────────────────

resource "aws_cloudwatch_log_group" "websocket" {
  name              = "/aws/lambda/${local.name}-websocket"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_lambda_function" "websocket" {
  function_name = "${local.name}-websocket"
  role          = aws_iam_role.lambda.arn
  handler       = "app.websocket.handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.websocket]
  tags       = var.tags

  lifecycle {
    ignore_changes = [filename, source_code_hash, s3_bucket, s3_key]
  }
}

# ─── Lambda: WebSocket ブロードキャスター ─────────────────
# DynamoDB Streams → 全 WebSocket クライアントに push

resource "aws_cloudwatch_log_group" "ws_broadcaster" {
  name              = "/aws/lambda/${local.name}-ws-broadcaster"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_lambda_function" "ws_broadcaster" {
  function_name = "${local.name}-ws-broadcaster"
  role          = aws_iam_role.lambda.arn
  handler       = "lambda_handlers.websocket_broadcaster.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.ws_broadcaster]
  tags       = var.tags

  lifecycle {
    ignore_changes = [filename, source_code_hash, s3_bucket, s3_key]
  }
}

# DynamoDB Streams → ws_broadcaster のトリガー
resource "aws_lambda_event_source_mapping" "robots_stream" {
  event_source_arn  = var.dynamodb_robots_stream_arn
  function_name     = aws_lambda_function.ws_broadcaster.arn
  starting_position = "LATEST"
  batch_size        = 10
}

# ─── Lambda: スケジューラートリガー ───────────────────────

resource "aws_cloudwatch_log_group" "scheduler_trigger" {
  name              = "/aws/lambda/${local.name}-scheduler-trigger"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_lambda_function" "scheduler_trigger" {
  function_name = "${local.name}-scheduler-trigger"
  role          = aws_iam_role.lambda.arn
  handler       = "lambda_handlers.scheduler_trigger.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.placeholder.output_path
  source_code_hash = data.archive_file.placeholder.output_base64sha256

  environment {
    variables = local.common_env
  }

  depends_on = [aws_cloudwatch_log_group.scheduler_trigger]
  tags       = var.tags

  lifecycle {
    ignore_changes = [filename, source_code_hash, s3_bucket, s3_key]
  }
}
