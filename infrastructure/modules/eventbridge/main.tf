locals {
  name = "${var.prefix}-${var.env}"
}

# スケジューラーグループ (スケジュール一覧の管理単位)
resource "aws_scheduler_schedule_group" "main" {
  name = local.name
  tags = var.tags
}

# EventBridge Scheduler → Lambda を呼び出す IAM Role
resource "aws_iam_role" "scheduler" {
  name = "${local.name}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "invoke-lambda"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = var.scheduler_trigger_lambda_arn
    }]
  })
}
