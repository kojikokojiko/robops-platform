output "http_api_endpoint" {
  value = module.api_gateway.http_api_endpoint
}

output "websocket_api_endpoint" {
  value = module.api_gateway.websocket_api_endpoint
}

output "cloudfront_domain" {
  value = "https://${module.s3_cloudfront.cloudfront_domain_name}"
}

output "frontend_bucket" {
  value = module.s3_cloudfront.frontend_bucket_name
}

output "cloudfront_distribution_id" {
  value = module.s3_cloudfront.cloudfront_distribution_id
}

output "lambda_artifacts_bucket" {
  value = module.s3_cloudfront.lambda_artifacts_bucket_name
}

output "ecr_repository_url" {
  value = module.ecs_emulator.ecr_repository_url
}

output "ecs_cluster_name" {
  value = module.ecs_emulator.ecs_cluster_name
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "cognito_client_id" {
  value = module.cognito.client_id
}
