output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.eks.endpoint
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = aws_eks_cluster.eks.name
}

output "configure_kubectl" {
  description = "CLI command to configure kubectl credentials"
  value       = "aws eks --region ${var.aws_region} update-kubeconfig --name ${aws_eks_cluster.eks.name}"
}
