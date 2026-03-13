locals {
  name = "${var.prefix}-${var.env}"
}

# ─── HTTP API (REST) ────────────────────────────────────

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name}-http"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }

  tags = var.tags
}

resource "aws_apigatewayv2_stage" "http" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.http_api.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
    })
  }

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "http_api" {
  name              = "/aws/apigateway/${local.name}-http"
  retention_in_days = 7
  tags              = var.tags
}

# Cognito オーソライザー
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.http.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito"

  jwt_configuration {
    audience = []
    issuer   = replace(var.cognito_user_pool_arn, ":user-pool/", ".auth.ap-northeast-1.amazoncognito.com/")
  }
}

# Lambda integration
resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.api_lambda_invoke_arn
  payload_format_version = "2.0"
}

# 全ルートを Lambda に転送 (FastAPI がルーティングを管理)
resource "aws_apigatewayv2_route" "api_proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_route" "api_root" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_lambda_permission" "http_api" {
  statement_id  = "AllowHTTPAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.api_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

# ─── WebSocket API ──────────────────────────────────────

resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${local.name}-websocket"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"

  tags = var.tags
}

resource "aws_apigatewayv2_stage" "websocket" {
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = var.env
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.websocket_api.arn
    format = jsonencode({
      requestId  = "$context.requestId"
      routeKey   = "$context.routeKey"
      status     = "$context.status"
      connectionId = "$context.connectionId"
    })
  }

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "websocket_api" {
  name              = "/aws/apigateway/${local.name}-websocket"
  retention_in_days = 7
  tags              = var.tags
}

resource "aws_apigatewayv2_integration" "websocket" {
  api_id                 = aws_apigatewayv2_api.websocket.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.websocket_lambda_invoke_arn
  content_handling_strategy = "CONVERT_TO_TEXT"
  passthrough_behavior      = "WHEN_NO_MATCH"
}

resource "aws_apigatewayv2_route" "ws_connect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.websocket.id}"
}

resource "aws_apigatewayv2_route" "ws_disconnect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.websocket.id}"
}

resource "aws_apigatewayv2_route" "ws_default" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.websocket.id}"
}

resource "aws_lambda_permission" "websocket_api" {
  statement_id  = "AllowWebSocketAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.websocket_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/*"
}
