variable "image_tag" {
  description = "Commit SHA of the independently built Temporal server image."
  type        = string
}

variable "region" {
  type = string
}

variable "state_bucket" {
  type = string
}

variable "env" {
  type = string
}

variable "project_name" {
  type = string
}

variable "team_name" {
  type = string
}

variable "repository_name" {
  type = string
}

variable "github_org" {
  type    = string
  default = "github.com/i-dot-ai/"
}

variable "deployed_via" {
  type    = string
  default = "GitHub_Actions"
}

variable "security_level" {
  type    = string
  default = "base"
}
