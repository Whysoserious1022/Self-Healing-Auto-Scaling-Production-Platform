variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the EKS Cluster"
  type        = string
  default     = "production-platform-cluster"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the production VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_instance_types" {
  description = "EC2 instance types for EKS managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "min_nodes" {
  description = "Minimum nodes in EKS auto-scaling group"
  type        = number
  default     = 2
}

variable "max_nodes" {
  description = "Maximum nodes in EKS auto-scaling group"
  type        = number
  default     = 5
}

variable "desired_nodes" {
  description = "Desired initial nodes in EKS auto-scaling group"
  type        = number
  default     = 2
}
