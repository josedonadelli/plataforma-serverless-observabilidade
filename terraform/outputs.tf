output "region" {
  description = "Região AWS em uso."
  value       = var.region
}

output "name_prefix" {
  description = "Prefixo resolvido usado nos nomes dos recursos."
  value       = local.prefix
}

output "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB de logs."
  value       = aws_dynamodb_table.logs.name
}

output "dynamodb_table_arn" {
  description = "ARN da tabela DynamoDB de logs."
  value       = aws_dynamodb_table.logs.arn
}

output "sqs_queue_url" {
  description = "URL da fila principal de logs."
  value       = aws_sqs_queue.logs.url
}

output "sqs_queue_arn" {
  description = "ARN da fila principal de logs."
  value       = aws_sqs_queue.logs.arn
}

output "sqs_dlq_url" {
  description = "URL da dead-letter queue."
  value       = aws_sqs_queue.logs_dlq.url
}

output "lambda_function_names" {
  description = "Nomes das funções Lambda."
  value = {
    ingestion = aws_lambda_function.ingestion.function_name
    query     = aws_lambda_function.query.function_name
    processor = aws_lambda_function.processor.function_name
  }
}
