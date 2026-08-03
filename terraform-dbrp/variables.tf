variable "postgres_password" {
  description = "Master password for PostgreSQL RDS instance"
  type        = string
  sensitive   = true
}

variable "mysql_password" {
  description = "Master password for MySQL RDS instance"
  type        = string
  sensitive   = true
}

variable "slack_webhook_url" {
  description = "Slack incoming webhook URL for alerts"
  type        = string
  sensitive   = true
}