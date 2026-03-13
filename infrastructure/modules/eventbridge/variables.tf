variable "env" {
  type = string
}

variable "prefix" {
  type    = string
  default = "robops"
}

variable "scheduler_trigger_lambda_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
