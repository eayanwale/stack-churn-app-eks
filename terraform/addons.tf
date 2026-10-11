# ---- In-cluster add-ons (installed with Helm) --------------------------------

resource "helm_release" "lb_controller" {
  name       = "aws-load-balancer-controller"
  namespace  = "kube-system"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = var.LB_CONTROLLER_CHART_VERSION

  set {
    name  = "clusterName"
    value = aws_eks_cluster.this.name
  }
  set {
    name  = "region"
    value = var.AWS_REGION
  }
  set {
    name  = "vpcId"
    value = var.VPC_ID
  }
  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }
  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = aws_iam_role.lb_controller.arn
  }

  depends_on = [
    aws_eks_node_group.default,
    aws_iam_role_policy_attachment.lb_controller,
    aws_ec2_tag.subnet_elb,
  ]
}

resource "helm_release" "argocd" {
  name             = "argocd"
  namespace        = "argocd"
  create_namespace = true
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = var.ARGOCD_CHART_VERSION

  depends_on = [aws_eks_node_group.default]
}

# The ArgoCD Application that auto-syncs k8s/ (same as argocd/application.yaml).
# Destroy order matters: this goes before the LB controller, so ArgoCD prunes
# the Ingress and the controller can delete the ALB it created.
resource "helm_release" "argocd_apps" {
  name       = "argocd-apps"
  namespace  = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argocd-apps"
  version    = var.ARGOCD_APPS_CHART_VERSION

  values = [yamlencode({
    applications = {
      stackit-churn = {
        namespace  = "argocd"
        finalizers = ["resources-finalizer.argocd.argoproj.io"]
        project    = "default"
        source = {
          repoURL        = var.GITOPS_REPO_URL
          targetRevision = var.GITOPS_REVISION
          path           = var.GITOPS_PATH
        }
        destination = {
          server    = "https://kubernetes.default.svc"
          namespace = var.APP_NAMESPACE
        }
        syncPolicy = {
          automated   = { prune = true, selfHeal = true }
          syncOptions = ["CreateNamespace=true"]
        }
      }
    }
  })]

  depends_on = [helm_release.argocd, helm_release.lb_controller]
}
