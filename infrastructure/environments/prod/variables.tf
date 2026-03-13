variable "iot_endpoint" {
  description = "AWS IoT Core endpoint"
  type        = string
}

variable "callback_urls" {
  description = "Cognito OAuth callback URLs (e.g. CloudFront domain)"
  type        = list(string)
}

variable "logout_urls" {
  description = "Cognito OAuth logout URLs"
  type        = list(string)
}
