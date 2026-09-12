# IAM roles das Lambdas, com permissões mínimas por função.

# Documento de trust: permite que o serviço Lambda assuma as roles.
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Permissão de escrever logs no CloudWatch — comum às três Lambdas.
locals {
  lambda_logs_managed_policy = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---------------------------------------------------------------------------
# Lambda processadora: consome SQS, escreve no DynamoDB, loga no CloudWatch.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "processor" {
  name               = "${local.prefix}-processor-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "processor" {
  statement {
    sid    = "ConsumeQueue"
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.logs.arn]
  }

  statement {
    sid       = "WriteLogs"
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.logs.arn]
  }
}

resource "aws_iam_role_policy" "processor" {
  name   = "${local.prefix}-processor-policy"
  role   = aws_iam_role.processor.id
  policy = data.aws_iam_policy_document.processor.json
}

resource "aws_iam_role_policy_attachment" "processor_logs" {
  role       = aws_iam_role.processor.name
  policy_arn = local.lambda_logs_managed_policy
}

# ---------------------------------------------------------------------------
# Lambda de ingestão (POST /logs): publica na fila SQS.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "ingestion" {
  name               = "${local.prefix}-ingestion-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "ingestion" {
  statement {
    sid       = "SendToQueue"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.logs.arn]
  }
}

resource "aws_iam_role_policy" "ingestion" {
  name   = "${local.prefix}-ingestion-policy"
  role   = aws_iam_role.ingestion.id
  policy = data.aws_iam_policy_document.ingestion.json
}

resource "aws_iam_role_policy_attachment" "ingestion_logs" {
  role       = aws_iam_role.ingestion.name
  policy_arn = local.lambda_logs_managed_policy
}

# ---------------------------------------------------------------------------
# Lambda de query (GET /logs): lê do DynamoDB.
# ---------------------------------------------------------------------------
resource "aws_iam_role" "query" {
  name               = "${local.prefix}-query-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "query" {
  statement {
    sid    = "ReadLogs"
    effect = "Allow"
    actions = [
      "dynamodb:Query",
      "dynamodb:GetItem",
    ]
    resources = [aws_dynamodb_table.logs.arn]
  }
}

resource "aws_iam_role_policy" "query" {
  name   = "${local.prefix}-query-policy"
  role   = aws_iam_role.query.id
  policy = data.aws_iam_policy_document.query.json
}

resource "aws_iam_role_policy_attachment" "query_logs" {
  role       = aws_iam_role.query.name
  policy_arn = local.lambda_logs_managed_policy
}
