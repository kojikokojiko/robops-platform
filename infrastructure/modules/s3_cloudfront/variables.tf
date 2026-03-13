variable "env" {
  type = string
}

variable "prefix" {
  type    = string
  default = "robops"
}

variable "tags" {
  type    = map(string)
  default = {}
}
