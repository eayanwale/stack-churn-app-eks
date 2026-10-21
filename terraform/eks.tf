# Current AWS account, used to build ARNs
data "aws_caller_identity" "current" {}

# Existing subnets the cluster and nodes run in
locals {
  subnet_ids = [var.SUBNET_A, var.SUBNET_B]
}

# Subnet tags the AWS Load Balancer Controller looks for when it creates the ALB
resource "aws_ec2_tag" "subnet_elb" {
  for_each    = toset(local.subnet_ids)
  resource_id = each.value
  key         = "kubernetes.io/role/elb"
  value       = "1"
}

resource "aws_ec2_tag" "subnet_cluster" {
  for_each    = toset(local.subnet_ids)
  resource_id = each.value
  key         = "kubernetes.io/cluster/${var.CLUSTER_NAME}"
  value       = "shared"
}

# Control plane: IAM role EKS assumes to manage the cluster
resource "aws_iam_role" "cluster" {
  name = "${var.CLUSTER_NAME}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# The EKS cluster. API auth mode uses access entries instead of the aws-auth ConfigMap,
# and whoever runs Terraform (the GitHub Actions role) is made cluster admin.
resource "aws_eks_cluster" "this" {
  name     = var.CLUSTER_NAME
  version  = var.CLUSTER_VERSION
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = local.subnet_ids
    endpoint_public_access  = true
    endpoint_private_access = true
  }

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }

  depends_on = [aws_iam_role_policy_attachment.cluster]
}

# Extra kubectl admins (e.g. your own IAM user), on top of the pipeline role.
resource "aws_eks_access_entry" "admin" {
  for_each      = toset(var.ADMIN_PRINCIPAL_ARNS)
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = each.value
}

# Give those principals the cluster admin policy
resource "aws_eks_access_policy_association" "admin" {
  for_each      = toset(var.ADMIN_PRINCIPAL_ARNS)
  cluster_name  = aws_eks_cluster.this.name
  principal_arn = each.value
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.admin]
}

# Worker nodes: IAM role the EC2 nodes run as
resource "aws_iam_role" "node" {
  name = "${var.CLUSTER_NAME}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# AWS managed policies every EKS node needs (join the cluster, pod networking, ECR pulls)
resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly", # pull from ECR
  ])
  role       = aws_iam_role.node.name
  policy_arn = each.value
}

# Managed node group that runs the app pods, ArgoCD and the LB controller
resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.CLUSTER_NAME}-default"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = local.subnet_ids
  instance_types  = [var.NODE_INSTANCE_TYPE]

  scaling_config {
    min_size     = var.NODE_MIN
    desired_size = var.NODE_DESIRED
    max_size     = var.NODE_MAX
  }

  update_config {
    max_unavailable = 1
  }

  # Scaling may change desired_size at runtime; don't fight it.
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }

  depends_on = [aws_iam_role_policy_attachment.node]
}