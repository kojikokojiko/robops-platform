variable "env" {
  type = string
}

variable "prefix" {
  type    = string
  default = "robops"
}

variable "robot_ids" {
  description = "List of robot IDs to create as IoT Things"
  type        = list(string)
  default     = ["robot-001", "robot-002", "robot-003", "robot-004", "robot-005"]
}

variable "telemetry_processor_lambda_arn" {
  description = "ARN of the Lambda function that processes telemetry"
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
