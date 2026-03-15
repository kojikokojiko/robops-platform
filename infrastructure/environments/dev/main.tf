terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.6"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"

  default_tags {
    tags = local.common_tags
  }
}

locals {
  env    = "dev"
  prefix = "robops"

  common_tags = {
    Project     = "robops-platform"
    Environment = local.env
    ManagedBy   = "terraform"
  }
}

# ─── S3 ─────────────────────────────────────────────────

resource "aws_s3_bucket" "lambda_artifacts" {
  bucket = "${local.prefix}-${local.env}-lambda-artifacts"
  tags   = local.common_tags
}

resource "aws_s3_bucket" "ota_firmware" {
  bucket = "${local.prefix}-${local.env}-ota-firmware"
  tags   = local.common_tags
}

# ─── DynamoDB ───────────────────────────────────────────

module "dynamodb" {
  source = "../../modules/dynamodb"
  env    = local.env
  prefix = local.prefix
  tags   = local.common_tags
}

# ─── Lambda ─────────────────────────────────────────────

module "lambda" {
  source = "../../modules/lambda"
  env    = local.env
  prefix = local.prefix
  region = "ap-northeast-1"

  dynamodb_robots_table_name         = module.dynamodb.robots_table_name
  dynamodb_schedules_table_name      = module.dynamodb.schedules_table_name
  dynamodb_ota_jobs_table_name       = module.dynamodb.ota_jobs_table_name
  dynamodb_ws_connections_table_name = module.dynamodb.websocket_connections_table_name
  dynamodb_robots_table_arn          = module.dynamodb.robots_table_arn
  dynamodb_schedules_table_arn       = module.dynamodb.schedules_table_arn
  dynamodb_ota_jobs_table_arn        = module.dynamodb.ota_jobs_table_arn
  dynamodb_ws_connections_table_arn  = module.dynamodb.websocket_connections_table_arn
  dynamodb_telemetry_table_name      = module.dynamodb.telemetry_table_name
  dynamodb_telemetry_table_arn       = module.dynamodb.telemetry_table_arn
  dynamodb_robots_stream_arn         = module.dynamodb.robots_stream_arn

  ota_firmware_bucket_name = aws_s3_bucket.ota_firmware.bucket
  ota_firmware_bucket_arn  = aws_s3_bucket.ota_firmware.arn

  iot_endpoint                   = var.iot_endpoint
  eventbridge_scheduler_role_arn = module.eventbridge.scheduler_role_arn
  eventbridge_schedule_group     = module.eventbridge.schedule_group_name
  websocket_api_endpoint         = module.api_gateway.websocket_api_endpoint

  tags = local.common_tags
}

# ─── API Gateway ────────────────────────────────────────

module "api_gateway" {
  source = "../../modules/api_gateway"
  env    = local.env
  prefix = local.prefix

  api_lambda_arn        = module.lambda.api_function_arn
  api_lambda_invoke_arn = module.lambda.api_invoke_arn

  websocket_lambda_arn        = module.lambda.websocket_function_arn
  websocket_lambda_invoke_arn = module.lambda.websocket_invoke_arn

  tags = local.common_tags
}

# ─── IoT Core ───────────────────────────────────────────

module "iot_core" {
  source = "../../modules/iot_core"
  env    = local.env
  prefix = local.prefix

  telemetry_processor_lambda_arn = module.lambda.telemetry_processor_function_arn

  tags = local.common_tags
}

# ─── EventBridge Scheduler ──────────────────────────────

module "eventbridge" {
  source = "../../modules/eventbridge"
  env    = local.env
  prefix = local.prefix

  scheduler_trigger_lambda_arn = module.lambda.scheduler_trigger_function_arn

  tags = local.common_tags
}
