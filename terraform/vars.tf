variable "AWS_REGION" {
  type    = string
  default = "us-east-1"
}

variable "CLUSTER_NAME" {
  type    = string
  default = "stackit-churn-eks"
}

variable "CLUSTER_VERSION" {
  type    = string
  default = "1.33"
}

# Existing network, shared with the Docker/EC2 stack.
variable "VPC_ID" {
  type    = string
  default = "vpc-0513533f2f1efbfbd"
}

variable "SUBNET_A" {
  type    = string
  default = "subnet-0cd407c60e5fc2301"
}

variable "SUBNET_B" {
  type    = string
  default = "subnet-004ef57820b789ae3"
}

variable "NODE_INSTANCE_TYPE" {
  type    = string
  default = "t3.medium"
}

variable "NODE_MIN" {
  type    = number
  default = 1
}

variable "NODE_DESIRED" {
  type    = number
  default = 2
}

variable "NODE_MAX" {
  type    = number
  default = 4
}

# IAM principals (users/roles) that should get kubectl admin on the cluster.
# The identity running Terraform (the GitHub Actions role) is always admin.
variable "ADMIN_PRINCIPAL_ARNS" {
  type    = list(string)
  default = []
}

# GitOps: ArgoCD watches this repo/path for the kustomize manifests.
variable "GITOPS_REPO_URL" {
  type        = string
  description = "HTTPS URL of the GitHub repo holding k8s/ (e.g. https://github.com/<org>/stackit-churn-app_eks.git)"
}

variable "GITOPS_REVISION" {
  type    = string
  default = "main"
}

variable "GITOPS_PATH" {
  type    = string
  default = "k8s"
}

variable "APP_NAMESPACE" {
  type    = string
  default = "stackit-churn"
}

variable "APP_SERVICE_ACCOUNT" {
  type    = string
  default = "churn-sa" # k8s/serviceaccount.yaml
}

variable "ARGOCD_CHART_VERSION" {
  type    = string
  default = "7.7.11"
}

variable "ARGOCD_APPS_CHART_VERSION" {
  type    = string
  default = "2.0.2"
}

variable "LB_CONTROLLER_CHART_VERSION" {
  type    = string
  default = "1.11.0"
}
