variable "env" {
  type = string
}

variable "prefix" {
  type    = string
  default = "robops"
}

variable "region" {
  type = string
}

variable "lambda_artifacts_bucket" {
  description = "S3 bucket for Lambda ZIP artifacts"
  type        = string
}

variable "dynamodb_robots_table_name" {
  type = string
}

variable "dynamodb_schedules_table_name" {
  type = string
}

variable "dynamodb_ota_jobs_table_name" {
  type = string
}

variable "dynamodb_ws_connections_table_name" {
  type = string
}

variable "dynamodb_robots_table_arn" {
  type = string
}

variable "dynamodb_schedules_table_arn" {
  type = string
}

variable "dynamodb_ota_jobs_table_arn" {
  type = string
}

variable "dynamodb_ws_connections_table_arn" {
  type = string
}

variable "dynamodb_telemetry_table_name" {
  type = string
}

variable "dynamodb_telemetry_table_arn" {
  type = string
}

variable "dynamodb_robots_stream_arn" {
  type = string
}

variable "ota_firmware_bucket_name" {
  type = string
}

variable "ota_firmware_bucket_arn" {
  type = string
}

variable "cognito_user_pool_arn" {
  type = string
}

variable "iot_endpoint" {
  type = string
}

variable "eventbridge_scheduler_role_arn" {
  type = string
}

variable "eventbridge_schedule_group" {
  type = string
}

variable "websocket_api_endpoint" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
