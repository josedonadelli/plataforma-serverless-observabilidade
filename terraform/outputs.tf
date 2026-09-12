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
