provider "aws" {
  region = var.AWS_REGION
}

# Helm talks to the cluster this stack creates. A short-lived token is fetched
# with the AWS CLI on every run, so nothing is stored in state or on disk.
provider "helm" {
  kubernetes {
    host                   = aws_eks_cluster.this.endpoint
    cluster_ca_certificate = base64decode(aws_eks_cluster.this.certificate_authority[0].data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.this.name, "--region", var.AWS_REGION]
    }
  }
}
