output "http_api_endpoint" {
  description = "REST API endpoint URL"
  value       = module.api_gateway.http_api_endpoint
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint URL"
  value       = module.api_gateway.websocket_api_endpoint
}

output "lambda_artifacts_bucket" {
  description = "S3 bucket for Lambda ZIP artifacts"
  value       = aws_s3_bucket.lambda_artifacts.bucket
}

output "ota_firmware_bucket" {
  description = "S3 bucket for OTA firmware manifests"
  value       = aws_s3_bucket.ota_firmware.bucket
}
