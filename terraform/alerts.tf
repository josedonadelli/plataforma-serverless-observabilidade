# Tópico SNS de alertas + alarme CloudWatch base.

resource "aws_sns_topic" "alerts" {
  name = "${local.prefix}-alerts"
}

# Assinatura de e-mail (exige confirmação manual no link recebido).
# Só é criada quando alert_email é informado.
resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Alarme base: dispara quando mensagens caem na DLQ (falha de processamento).
# O alarme de pico de ERROR (threshold detalhado) entra numa etapa posterior.
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${local.prefix}-dlq-nao-vazia"
  alarm_description   = "Há mensagens na DLQ — falha no processamento de logs."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  period              = 300
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.logs_dlq.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# Alarme de pico de erros: dispara quando a soma de logs ERROR em 5 min
# ultrapassa o threshold. Métrica custom emitida pela Lambda processadora.
resource "aws_cloudwatch_metric_alarm" "error_spike" {
  alarm_name          = "${local.prefix}-pico-de-erros"
  alarm_description   = "Muitos logs ERROR em 5 min — possível incidente."
  namespace           = local.metric_namespace
  metric_name         = local.error_metric_name
  statistic           = "Sum"
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.error_alarm_threshold
  period              = 300
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}
