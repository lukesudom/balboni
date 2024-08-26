# provider.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "balboni-state"
    key            = "repo-scanner/terraform.tfstate"
    region         = "ap-southeast-2"  # Adjust to your preferred region
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.region
}