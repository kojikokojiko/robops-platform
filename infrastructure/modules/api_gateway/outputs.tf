output "http_api_id" {
  value = aws_apigatewayv2_api.http.id
}

output "http_api_endpoint" {
  value = aws_apigatewayv2_stage.http.invoke_url
}

output "websocket_api_id" {
  value = aws_apigatewayv2_api.websocket.id
}

output "websocket_api_endpoint" {
  value = aws_apigatewayv2_stage.websocket.invoke_url
}

output "websocket_api_execution_arn" {
  value = aws_apigatewayv2_api.websocket.execution_arn
}
