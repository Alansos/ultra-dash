terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = "us-east-1" }

# Billing tripwire: email me if spend passes 80% of $5
resource "aws_budgets_budget" "spend_guard" {
  name         = "monthly-spend-guard"
  budget_type  = "COST"
  limit_amount = "5"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = ["lopezalan27@outlook.com"]
  }
}

# S3 bucket for GPX backups (near-zero cost)
resource "aws_s3_bucket" "gpx_backups" {
  bucket = "ultra-dash-gpx-backups-alanlopez27"
}
