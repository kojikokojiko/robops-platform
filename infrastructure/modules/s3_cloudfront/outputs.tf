output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend.bucket
}

output "frontend_bucket_arn" {
  value = aws_s3_bucket.frontend.arn
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "lambda_artifacts_bucket_name" {
  value = aws_s3_bucket.lambda_artifacts.bucket
}

output "lambda_artifacts_bucket_arn" {
  value = aws_s3_bucket.lambda_artifacts.arn
}

output "ota_firmware_bucket_name" {
  value = aws_s3_bucket.ota_firmware.bucket
}

output "ota_firmware_bucket_arn" {
  value = aws_s3_bucket.ota_firmware.arn
}
