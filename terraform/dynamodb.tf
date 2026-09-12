# Tabela única de logs.
# PK = service, SK = timestamp (ISO 8601). Filtro por level via FilterExpression (sem GSI).
resource "aws_dynamodb_table" "logs" {
  name         = local.prefix
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "service"
  range_key = "timestamp"

  attribute {
    name = "service"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  # Expiração automática de logs antigos.
  ttl {
    attribute_name = "expire_at"
    enabled        = true
  }
}
