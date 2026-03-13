variable "env" {
  description = "Environment name (dev / prod)"
  type        = string
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "robops"
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
