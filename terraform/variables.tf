variable "region" {
  description = "Região AWS onde os recursos serão criados."
  type        = string
  default     = "sa-east-1"
}

variable "name_prefix" {
  description = "Prefixo aplicado ao nome dos recursos, para evitar colisões e agrupar por projeto."
  type        = string
  default     = "logs"
}

variable "environment" {
  description = "Ambiente lógico (ex.: dev, prod). Usado em nomes e tags."
  type        = string
  default     = "dev"
}

variable "processor_timeout_seconds" {
  description = "Timeout da Lambda processadora. Base para o visibility timeout da fila SQS."
  type        = number
  default     = 30
}

variable "max_receive_count" {
  description = "Tentativas de processamento antes de a mensagem ir para a DLQ."
  type        = number
  default     = 3
}

variable "alert_email" {
  description = "E-mail que recebe os alertas via SNS. Vazio não cria assinatura."
  type        = string
  default     = ""
}
