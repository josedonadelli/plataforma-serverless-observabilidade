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
