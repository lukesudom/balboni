variable "region" {
  description = "AWS region"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "discord_webhook_url" {
  description = "Discord Webhook URL"
  type        = string
}

variable "git_username" {
  description = "Git Username for cloning repositories"
  type        = string
}

variable "git_token" {
  description = "Git Token for cloning repositories"
  type        = string
  sensitive   = true
}

variable "image_tag" {
  description = "Tag for the Docker images"
  type        = string
  default     = "latest"
}