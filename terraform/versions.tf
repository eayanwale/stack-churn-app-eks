terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.17" # 3.x changed the provider block syntax
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Same state bucket as the Docker/EC2 stack, different key.
  backend "s3" {
    bucket       = "enoch-tf-state-bucket"
    key          = "stackit-churn-app-eks/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true # S3 native locking (Terraform >= 1.10), no DynamoDB table
  }
}
