variable "env" {
  description = "Environment name (dev / prod)"
  type        = string
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "robops"
}

variable "magnetic_store_retention_days" {
  description = "Retention period in magnetic store (days)"
  type        = number
  default     = 365
}

variable "memory_store_retention_hours" {
  description = "Retention period in memory store (hours)"
  type        = number
  default     = 24
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
