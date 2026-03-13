variable "env" {
  description = "Environment name (dev / prod)"
  type        = string
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "robops"
}

variable "callback_urls" {
  description = "OAuth callback URLs"
  type        = list(string)
}

variable "logout_urls" {
  description = "OAuth logout URLs"
  type        = list(string)
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
