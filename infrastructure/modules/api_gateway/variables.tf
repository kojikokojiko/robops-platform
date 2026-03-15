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

variable "tags" {
  type    = map(string)
  default = {}
}
