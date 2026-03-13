locals {
  name = "${var.prefix}-${var.env}"
}

# ─── ECR ────────────────────────────────────────────────

resource "aws_ecr_repository" "emulator" {
  name                 = "${local.name}-robot-emulator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "emulator" {
  repository = aws_ecr_repository.emulator.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# ─── ECS Cluster ────────────────────────────────────────

resource "aws_ecs_cluster" "emulators" {
  name = "${local.name}-emulators"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# ─── IAM Role for ECS Tasks ─────────────────────────────

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution_basic" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_secrets" {
  name = "read-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = values(var.robot_secret_arns)
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

# ─── CloudWatch Log Group ────────────────────────────────

resource "aws_cloudwatch_log_group" "emulator" {
  for_each = toset(var.robot_ids)

  name              = "/ecs/${local.name}/${each.value}"
  retention_in_days = 7
  tags              = var.tags
}

# ─── ECS Task Definitions ────────────────────────────────
# 各ロボットに個別のタスク定義 (ROBOT_ID と証明書が異なる)

resource "aws_ecs_task_definition" "robot" {
  for_each = toset(var.robot_ids)

  family                   = "${local.name}-${each.value}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "robot"
    image = "${aws_ecr_repository.emulator.repository_url}:latest"

    environment = [
      { name = "ROBOT_ID", value = each.value },
      { name = "AWS_DEFAULT_REGION", value = var.region },
      { name = "IOT_ENDPOINT", value = var.iot_endpoint },
      { name = "CERT_SOURCE", value = "secrets_manager" },
      { name = "SECRET_NAME", value = var.robot_secret_names[each.value] },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/ecs/${local.name}/${each.value}"
        awslogs-region        = var.region
        awslogs-stream-prefix = "robot"
      }
    }

    essential = true
  }])

  tags = merge(var.tags, { robot_id = each.value })
}

# ─── ECS Services ────────────────────────────────────────
# デフォルト VPC のパブリックサブネットを使用 (IoT Core への outbound)

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "emulator" {
  name        = "${local.name}-emulator"
  description = "Robot emulator ECS tasks"
  vpc_id      = data.aws_vpc.default.id

  # IoT Core への MQTT (port 8883) outbound
  egress {
    from_port   = 8883
    to_port     = 8883
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS outbound (Secrets Manager, ECR)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${local.name}-emulator" })
}

resource "aws_ecs_service" "robot" {
  for_each = toset(var.robot_ids)

  name            = each.value
  cluster         = aws_ecs_cluster.emulators.id
  task_definition = aws_ecs_task_definition.robot[each.value].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.emulator.id]
    assign_public_ip = true
  }

  # コード更新後のローリングデプロイ
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  tags = merge(var.tags, { robot_id = each.value })

  lifecycle {
    # GitHub Actions による image 更新を Terraform が巻き戻さない
    ignore_changes = [task_definition]
  }
}
