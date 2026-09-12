# Fila de ingestão de logs + dead-letter queue.
# Mensagens que falharem o processamento maxReceiveCount vezes vão para a DLQ.

# Dead-letter queue: retém mensagens que não puderam ser processadas.
resource "aws_sqs_queue" "logs_dlq" {
  name                      = "${local.prefix}-dlq"
  message_retention_seconds = 1209600 # 14 dias (máximo)
}

# Fila principal consumida pela Lambda processadora.
resource "aws_sqs_queue" "logs" {
  name = "${local.prefix}-queue"

  # Deve ser >= timeout da Lambda processadora. AWS recomenda ~6x o timeout.
  visibility_timeout_seconds = var.processor_timeout_seconds * 6

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.logs_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}
