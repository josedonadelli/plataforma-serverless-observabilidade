# Recursos Lambda: empacotamento do código Python via archive_file,
# env vars injetadas e o mapeamento SQS -> processadora.

locals {
  functions_dir  = "${path.module}/../functions"
  lambda_runtime = "python3.12"
}

# --- Empacotamento (zip) de cada função ---
data "archive_file" "ingestion" {
  type        = "zip"
  source_dir  = "${local.functions_dir}/ingestion"
  output_path = "${path.module}/.build/ingestion.zip"
}

data "archive_file" "query" {
  type        = "zip"
  source_dir  = "${local.functions_dir}/query"
  output_path = "${path.module}/.build/query.zip"
}

data "archive_file" "processor" {
  type        = "zip"
  source_dir  = "${local.functions_dir}/processor"
  output_path = "${path.module}/.build/processor.zip"
}

# --- Lambda de ingestão (POST /logs) ---
resource "aws_lambda_function" "ingestion" {
  function_name    = "${local.prefix}-ingestion"
  role             = aws_iam_role.ingestion.arn
  runtime          = local.lambda_runtime
  handler          = "handler.handler"
  filename         = data.archive_file.ingestion.output_path
  source_code_hash = data.archive_file.ingestion.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      QUEUE_URL = aws_sqs_queue.logs.url
    }
  }
}

# --- Lambda de query (GET /logs) ---
resource "aws_lambda_function" "query" {
  function_name    = "${local.prefix}-query"
  role             = aws_iam_role.query.arn
  runtime          = local.lambda_runtime
  handler          = "handler.handler"
  filename         = data.archive_file.query.output_path
  source_code_hash = data.archive_file.query.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.logs.name
    }
  }
}

# --- Lambda processadora (SQS -> DynamoDB) ---
resource "aws_lambda_function" "processor" {
  function_name    = "${local.prefix}-processor"
  role             = aws_iam_role.processor.arn
  runtime          = local.lambda_runtime
  handler          = "handler.handler"
  filename         = data.archive_file.processor.output_path
  source_code_hash = data.archive_file.processor.output_base64sha256
  timeout          = var.processor_timeout_seconds

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.logs.name
    }
  }
}

# Dispara a processadora a partir das mensagens da fila.
resource "aws_lambda_event_source_mapping" "processor_sqs" {
  event_source_arn        = aws_sqs_queue.logs.arn
  function_name           = aws_lambda_function.processor.arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}
