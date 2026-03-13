output "http_api_endpoint" {
  description = "REST API endpoint URL"
  value       = module.api_gateway.http_api_endpoint
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint URL"
  value       = module.api_gateway.websocket_api_endpoint
}

output "cloudfront_domain" {
  description = "Dashboard URL"
  value       = "https://${module.s3_cloudfront.cloudfront_domain_name}"
}

output "frontend_bucket" {
  description = "S3 bucket for frontend assets"
  value       = module.s3_cloudfront.frontend_bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = module.s3_cloudfront.cloudfront_distribution_id
}

output "lambda_artifacts_bucket" {
  description = "S3 bucket for Lambda ZIP artifacts"
  value       = module.s3_cloudfront.lambda_artifacts_bucket_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for robot emulator image"
  value       = module.ecs_emulator.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name for robot emulators"
  value       = module.ecs_emulator.ecs_cluster_name
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "cognito_client_id" {
  value = module.cognito.client_id
}
