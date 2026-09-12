# Plataforma Serverless para Processamento e Análise de Logs em Tempo Real na AWS

Plataforma serverless para ingestão, processamento e consulta de logs em tempo real,
construída sobre AWS (API Gateway, SQS, Lambda, DynamoDB, CloudWatch e SNS) e provisionada
com Terraform. Projeto de TCC com custo-alvo de R$0 (free tier).

## Estrutura do repositório

```
terraform/   # Infraestrutura como código (IaC)
functions/   # Código das Lambdas (Python + boto3)
scripts/     # Scripts auxiliares (ex.: gerador de logs simulados)
```

## Arquitetura (resumo)

`POST /logs` → API Gateway → Lambda ingestão → SQS → Lambda processadora → DynamoDB
`GET /logs`  → API Gateway → Lambda query → DynamoDB
Erros `level=ERROR` → métrica CloudWatch → alarme → SNS (e-mail).

## Terraform

- **Provider:** AWS `~> 5.92`, região `sa-east-1`.
- **State:** local no início do projeto. Migração para backend S3 + lock em DynamoDB
  é uma evolução opcional — decisão a documentar aqui quando adotada.

```bash
cd terraform
terraform init
terraform plan
terraform apply
```
