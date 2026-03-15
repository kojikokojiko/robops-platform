variable "env" {
  type = string
}

variable "prefix" {
  type    = string
  default = "robops"
}

variable "api_lambda_arn" {
  type = string
}

variable "api_lambda_invoke_arn" {
  type = string
}

variable "websocket_lambda_arn" {
  type = string
}

variable "websocket_lambda_invoke_arn" {
  type = string
}

variable "cognito_user_pool_arn" {
  type = string
}

variable "cognito_user_pool_id" {
  type = string
}

variable "cognito_client_id" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
