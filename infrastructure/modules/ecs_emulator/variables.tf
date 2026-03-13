variable "env" {
  type = string
}

variable "prefix" {
  type    = string
  default = "robops"
}

variable "region" {
  type = string
}

variable "robot_ids" {
  description = "List of robot IDs to run as ECS tasks"
  type        = list(string)
  default     = ["robot-001", "robot-002", "robot-003", "robot-004", "robot-005"]
}

variable "iot_endpoint" {
  description = "AWS IoT Core endpoint (e.g. xxxxxxxxxx.iot.ap-northeast-1.amazonaws.com)"
  type        = string
}

variable "robot_secret_names" {
  description = "Map of robot_id => Secrets Manager secret name"
  type        = map(string)
}

variable "robot_secret_arns" {
  description = "Map of robot_id => Secrets Manager secret ARN"
  type        = map(string)
}

variable "cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 256
}

variable "memory" {
  description = "ECS task memory (MiB)"
  type        = number
  default     = 512
}

variable "tags" {
  type    = map(string)
  default = {}
}
