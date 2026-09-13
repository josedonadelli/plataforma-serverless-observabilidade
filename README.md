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

Todas as variáveis têm valor padrão em `variables.tf`, então o `apply` funciona sem
argumentos. Duas úteis de ajustar:

- `alert_email` — e-mail que recebe os alertas via SNS. Vazio (padrão) não cria a
  assinatura; ao informar, é preciso confirmar o link que o SNS envia por e-mail.
- `error_alarm_threshold` — número de logs `ERROR` em 5 min a partir do qual o alarme dispara.

```bash
terraform apply -var alert_email=voce@exemplo.com
```

Após o `apply`, a URL base da API fica no output `api_invoke_url`:

```bash
terraform output -raw api_invoke_url
```

## Uso da API

Nos exemplos abaixo, `API` aponta para a URL retornada em `api_invoke_url`.

### Enviar um log — `POST /logs`

Contrato do log: `service`, `level` (`INFO` | `WARN` | `ERROR`), `message` e `timestamp`
(ISO 8601) são obrigatórios; `trace_id` é opcional (gerado se ausente).

```bash
curl -X POST "$API/logs" \
  -H 'Content-Type: application/json' \
  -d '{
        "service": "auth-service",
        "level": "ERROR",
        "message": "falha ao autenticar",
        "timestamp": "2026-09-12T16:00:00Z"
      }'
# 202 {"status": "accepted", "trace_id": "..."}
```

### Consultar logs — `GET /logs`

Parâmetros: `service` (obrigatório), `level`, `start_time` / `end_time` (ISO 8601),
`limit` (1–200, padrão 50) e `cursor` (paginação).

```bash
# filtra por serviço e nível, 2 itens por página
curl "$API/logs?service=auth-service&level=ERROR&limit=2"
```

A resposta tem o formato `{ "items": [...], "count": N, "next_cursor": "<cursor|null>" }`.
Para a página seguinte, repita a chamada acrescentando `cursor=<next_cursor>`.

## Gerador de logs simulados

`scripts/log_generator.py` popula a plataforma com logs fictícios via `POST /logs`.

```bash
# fluxo sustentado: 60 logs a ~12/s, 15% de ERROR
python3 scripts/log_generator.py --url "$API" --count 60 --rate 12 --error-rate 0.15

# cenário de pico: eleva a proporção de ERROR e exercita o alarme
python3 scripts/log_generator.py --url "$API" --spike --count 25 --rate 8
```

Principais opções: `--rate` (vazão), `--count` (número fixo de logs), `--error-rate`,
`--spike` (cenário de pico), `--seed` (reprodutibilidade) e `--dry-run`. A lista completa
está em `--help`.

## Testes

Os testes são locais — sem AWS e sem rede (o `boto3` é mockado):

```bash
python3 scripts/test_processor.py
python3 scripts/test_api.py
python3 scripts/test_log_generator.py
```
