output "database_name" {
  value = aws_timestreamwrite_database.main.database_name
}

output "table_name" {
  value = aws_timestreamwrite_table.telemetry.table_name
}
