locals {
  name = "${var.prefix}-${var.env}"
}

resource "aws_timestreamwrite_database" "main" {
  database_name = local.name

  tags = merge(var.tags, { Name = local.name })
}

resource "aws_timestreamwrite_table" "telemetry" {
  database_name = aws_timestreamwrite_database.main.database_name
  table_name    = "telemetry"

  retention_properties {
    magnetic_store_retention_period_in_days = var.magnetic_store_retention_days
    memory_store_retention_period_in_hours  = var.memory_store_retention_hours
  }

  tags = merge(var.tags, { Name = "${local.name}-telemetry" })
}
