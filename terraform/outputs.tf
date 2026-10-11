output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.this.endpoint
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --name ${aws_eks_cluster.this.name} --region ${var.AWS_REGION}"
}

output "app_irsa_role_arn" {
  description = "Set as eks.amazonaws.com/role-arn in k8s/serviceaccount.yaml for INFERENCE_MODE=aws"
  value       = aws_iam_role.app.arn
}

output "argocd_password_command" {
  value = "kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
}
