# Recursos da plataforma serverless de logs.
# SQS, DynamoDB, IAM, Lambdas, API Gateway e SNS entram aqui.

locals {
  # Prefixo base para nomear recursos, ex.: "logs-dev".
  prefix = "${var.name_prefix}-${var.environment}"

  # Namespace da métrica custom de logs ERROR no CloudWatch.
  # Compartilhado entre a Lambda processadora e o alarme.
  metric_namespace  = "${local.prefix}/logs"
  error_metric_name = "ErrorLogs"
}
