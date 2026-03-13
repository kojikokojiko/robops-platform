output "api_function_name" {
  value = aws_lambda_function.api.function_name
}

output "api_function_arn" {
  value = aws_lambda_function.api.arn
}

output "api_invoke_arn" {
  value = aws_lambda_function.api.invoke_arn
}

output "telemetry_processor_function_name" {
  value = aws_lambda_function.telemetry_processor.function_name
}

output "telemetry_processor_function_arn" {
  value = aws_lambda_function.telemetry_processor.arn
}

output "websocket_function_name" {
  value = aws_lambda_function.websocket.function_name
}

output "websocket_function_arn" {
  value = aws_lambda_function.websocket.arn
}

output "websocket_invoke_arn" {
  value = aws_lambda_function.websocket.invoke_arn
}

output "scheduler_trigger_function_name" {
  value = aws_lambda_function.scheduler_trigger.function_name
}

output "scheduler_trigger_function_arn" {
  value = aws_lambda_function.scheduler_trigger.arn
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda.arn
}
