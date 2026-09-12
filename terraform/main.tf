# Recursos da plataforma serverless de logs.
# SQS, DynamoDB, IAM, Lambdas, API Gateway e SNS entram aqui.

locals {
  # Prefixo base para nomear recursos, ex.: "logs-dev".
  prefix = "${var.name_prefix}-${var.environment}"
}
