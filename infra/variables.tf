variable "aws_region" {
  description = "AWS region for ClaimSense AI infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "claimsense-ai"
}

variable "container_port" {
  description = "Port exposed by the FastAPI container"
  type        = number
  default     = 8000
}

variable "fargate_cpu" {
  description = "Fargate CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "fargate_memory" {
  description = "Fargate memory in MB (2048 = 2 GB)"
  type        = number
  default     = 2048
}
