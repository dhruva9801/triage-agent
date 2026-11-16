variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "triage"
}

variable "api_image_uri" {
  description = "Full image reference for the API, pinned by digest (repo@sha256:...). Set by CI."
  type        = string
}

variable "worker_image_uri" {
  description = "Full image reference for the worker, pinned by digest. Set by CI."
  type        = string
}

variable "alert_email" {
  description = "Receives budget and DLQ alarms. Confirm the SNS subscription email after first apply."
  type        = string
  sensitive   = true
}

variable "monthly_budget_usd" {
  type    = number
  default = 15
}

variable "log_retention_days" {
  description = "Without an explicit log group, Lambda logs are kept forever and billed forever."
  type        = number
  default     = 14
}

variable "worker_timeout_seconds" {
  type    = number
  default = 300
}
