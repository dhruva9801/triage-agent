resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project}-api"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.project}-worker"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "http_access" {
  name              = "/aws/apigateway/${var.project}-http"
  retention_in_days = var.log_retention_days
}
