# ---- IAM Roles for Service Accounts (IRSA) ----------------------------------
data "tls_certificate" "oidc" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.oidc.certificates[0].sha1_fingerprint]
}

locals {
  oidc_host = replace(aws_iam_openid_connect_provider.eks.url, "https://", "")
}

# --- AWS Load Balancer Controller (turns k8s/ingress.yaml into an ALB) -------
resource "aws_iam_policy" "lb_controller" {
  name   = "${var.CLUSTER_NAME}-lb-controller"
  policy = file("${path.module}/../iam_policy.json")
}

resource "aws_iam_role" "lb_controller" {
  name = "${var.CLUSTER_NAME}-lb-controller"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.eks.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
          "${local.oidc_host}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lb_controller" {
  role       = aws_iam_role.lb_controller.name
  policy_arn = aws_iam_policy.lb_controller.arn
}

# --- The app itself: SageMaker InvokeEndpoint for INFERENCE_MODE=aws ----------
resource "aws_iam_role" "app" {
  name = "churn-sagemaker-irsa"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.eks.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
          "${local.oidc_host}:sub" = "system:serviceaccount:${var.APP_NAMESPACE}:${var.APP_SERVICE_ACCOUNT}"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "app" {
  name = "invoke-churn-endpoint"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sagemaker:InvokeEndpoint"]
      Resource = "arn:aws:sagemaker:${var.AWS_REGION}:${data.aws_caller_identity.current.account_id}:endpoint/*"
    }]
  })
}
