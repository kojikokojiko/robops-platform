locals {
  name = "${var.prefix}-${var.env}"
}

# ─── Thing Group (フリート管理) ────────────────────────

resource "aws_iot_thing_group" "robots" {
  name = "${local.name}-robots"
  tags = var.tags
}

# ─── IoT Policy ────────────────────────────────────────
# 各ロボットは自分のトピックのみ pub/sub 可

resource "aws_iot_policy" "robot" {
  name = "${local.name}-robot-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["iot:Connect"]
        Resource = [
          "arn:aws:iot:*:*:client/$${iot:Connection.Thing.ThingName}"
        ]
      },
      {
        Effect = "Allow"
        Action = ["iot:Publish"]
        Resource = [
          "arn:aws:iot:*:*:topic/robots/$${iot:Connection.Thing.ThingName}/*",
          "arn:aws:iot:*:*:topic/$aws/things/$${iot:Connection.Thing.ThingName}/jobs/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["iot:Subscribe"]
        Resource = [
          "arn:aws:iot:*:*:topicfilter/robots/$${iot:Connection.Thing.ThingName}/commands",
          "arn:aws:iot:*:*:topicfilter/$aws/things/$${iot:Connection.Thing.ThingName}/jobs/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["iot:Receive"]
        Resource = [
          "arn:aws:iot:*:*:topic/robots/$${iot:Connection.Thing.ThingName}/commands",
          "arn:aws:iot:*:*:topic/$aws/things/$${iot:Connection.Thing.ThingName}/jobs/*"
        ]
      },
      {
        # IoT Jobs の進捗更新
        Effect = "Allow"
        Action = [
          "iot:UpdateThingShadow",
          "iot:GetThingShadow"
        ]
        Resource = [
          "arn:aws:iot:*:*:thing/$${iot:Connection.Thing.ThingName}"
        ]
      }
    ]
  })
}

# ─── IoT Things & Certificates ─────────────────────────

resource "aws_iot_thing" "robot" {
  for_each = toset(var.robot_ids)

  name = each.value

  attributes = {
    env = var.env
  }
}

resource "aws_iot_thing_group_membership" "robot" {
  for_each = toset(var.robot_ids)

  thing_name       = each.value
  thing_group_name = aws_iot_thing_group.robots.name

  depends_on = [aws_iot_thing.robot]
}

resource "aws_iot_certificate" "robot" {
  for_each = toset(var.robot_ids)
  active   = true
}

resource "aws_iot_thing_principal_attachment" "robot" {
  for_each = toset(var.robot_ids)

  thing     = each.value
  principal = aws_iot_certificate.robot[each.value].arn

  depends_on = [aws_iot_thing.robot, aws_iot_certificate.robot]
}

resource "aws_iot_policy_attachment" "robot" {
  for_each = toset(var.robot_ids)

  policy = aws_iot_policy.robot.name
  target = aws_iot_certificate.robot[each.value].arn
}

# ─── Secrets Manager (証明書の保存) ────────────────────
# ECS Fargate のエミュレータが起動時に読み込む

resource "aws_secretsmanager_secret" "robot_cert" {
  for_each = toset(var.robot_ids)

  name                    = "${local.name}/certs/${each.value}"
  recovery_window_in_days = 0 # 即時削除可能 (dev 向け)

  tags = merge(var.tags, { robot_id = each.value })
}

resource "aws_secretsmanager_secret_version" "robot_cert" {
  for_each = toset(var.robot_ids)

  secret_id = aws_secretsmanager_secret.robot_cert[each.value].id

  secret_string = jsonencode({
    certificate_pem = aws_iot_certificate.robot[each.value].certificate_pem
    private_key     = aws_iot_certificate.robot[each.value].private_key
    # AWS Root CA は公開されているので URL を持つだけで OK
    ca_url = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"
  })
}

# ─── Fleet Indexing ─────────────────────────────────────

resource "aws_iot_indexing_configuration" "main" {
  thing_indexing_configuration {
    thing_indexing_mode              = "REGISTRY_AND_SHADOW"
    thing_connectivity_indexing_mode = "STATUS"
  }
}

# ─── IoT Topic Rule: テレメトリ → Lambda ────────────────

resource "aws_iot_topic_rule" "telemetry" {
  name        = replace("${local.name}_telemetry", "-", "_")
  enabled     = true
  sql         = "SELECT * FROM 'robots/+/telemetry'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = var.telemetry_processor_lambda_arn
  }

  error_action {
    cloudwatch_logs {
      log_group_name = "/aws/iot/${local.name}/errors"
      role_arn       = aws_iam_role.iot_rule.arn
    }
  }
}

resource "aws_lambda_permission" "iot_telemetry" {
  statement_id  = "AllowIoTInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.telemetry_processor_lambda_arn
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.telemetry.arn
}

# ─── IAM Role for IoT Rules ─────────────────────────────

resource "aws_iam_role" "iot_rule" {
  name = "${local.name}-iot-rule-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "iot.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "iot_rule_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.iot_rule.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:*:*:*"
    }]
  })
}
