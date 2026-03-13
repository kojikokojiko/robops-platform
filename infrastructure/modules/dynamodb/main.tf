locals {
  name = "${var.prefix}-${var.env}"
}

# ロボット状態テーブル
resource "aws_dynamodb_table" "robots" {
  name         = "${local.name}-robots"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "robot_id"

  attribute {
    name = "robot_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }

  # WebSocket broadcaster 用の DynamoDB Streams
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = merge(var.tags, { Name = "${local.name}-robots" })
}

# スケジュールテーブル
resource "aws_dynamodb_table" "schedules" {
  name         = "${local.name}-schedules"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "schedule_id"
  range_key    = "robot_id"

  attribute {
    name = "schedule_id"
    type = "S"
  }

  attribute {
    name = "robot_id"
    type = "S"
  }

  global_secondary_index {
    name            = "robot-index"
    hash_key        = "robot_id"
    projection_type = "ALL"
  }

  tags = merge(var.tags, { Name = "${local.name}-schedules" })
}

# OTA ジョブテーブル
resource "aws_dynamodb_table" "ota_jobs" {
  name         = "${local.name}-ota-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"
  range_key    = "robot_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  attribute {
    name = "robot_id"
    type = "S"
  }

  global_secondary_index {
    name            = "robot-index"
    hash_key        = "robot_id"
    projection_type = "ALL"
  }

  tags = merge(var.tags, { Name = "${local.name}-ota-jobs" })
}

# WebSocket 接続管理テーブル
resource "aws_dynamodb_table" "websocket_connections" {
  name         = "${local.name}-ws-connections"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "connection_id"

  attribute {
    name = "connection_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = merge(var.tags, { Name = "${local.name}-ws-connections" })
}
