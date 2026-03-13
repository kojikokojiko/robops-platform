output "robots_table_name" {
  value = aws_dynamodb_table.robots.name
}

output "robots_table_arn" {
  value = aws_dynamodb_table.robots.arn
}

output "robots_stream_arn" {
  value = aws_dynamodb_table.robots.stream_arn
}

output "schedules_table_name" {
  value = aws_dynamodb_table.schedules.name
}

output "schedules_table_arn" {
  value = aws_dynamodb_table.schedules.arn
}

output "ota_jobs_table_name" {
  value = aws_dynamodb_table.ota_jobs.name
}

output "ota_jobs_table_arn" {
  value = aws_dynamodb_table.ota_jobs.arn
}

output "websocket_connections_table_name" {
  value = aws_dynamodb_table.websocket_connections.name
}

output "websocket_connections_table_arn" {
  value = aws_dynamodb_table.websocket_connections.arn
}
