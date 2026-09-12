output "region" {
  description = "Região AWS em uso."
  value       = var.region
}

output "name_prefix" {
  description = "Prefixo resolvido usado nos nomes dos recursos."
  value       = local.prefix
}
