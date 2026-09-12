# API Gateway REST: POST /logs -> ingestão, GET /logs -> query.

resource "aws_api_gateway_rest_api" "logs" {
  name        = "${local.prefix}-api"
  description = "API de ingestão e consulta de logs."
}

# Recurso /logs
resource "aws_api_gateway_resource" "logs" {
  rest_api_id = aws_api_gateway_rest_api.logs.id
  parent_id   = aws_api_gateway_rest_api.logs.root_resource_id
  path_part   = "logs"
}

# --- POST /logs -> Lambda de ingestão ---
resource "aws_api_gateway_method" "post_logs" {
  rest_api_id   = aws_api_gateway_rest_api.logs.id
  resource_id   = aws_api_gateway_resource.logs.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_logs" {
  rest_api_id             = aws_api_gateway_rest_api.logs.id
  resource_id             = aws_api_gateway_resource.logs.id
  http_method             = aws_api_gateway_method.post_logs.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ingestion.invoke_arn
}

# --- GET /logs -> Lambda de query ---
resource "aws_api_gateway_method" "get_logs" {
  rest_api_id   = aws_api_gateway_rest_api.logs.id
  resource_id   = aws_api_gateway_resource.logs.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_logs" {
  rest_api_id             = aws_api_gateway_rest_api.logs.id
  resource_id             = aws_api_gateway_resource.logs.id
  http_method             = aws_api_gateway_method.get_logs.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

# --- CORS: preflight OPTIONS /logs via integração MOCK ---
resource "aws_api_gateway_method" "options_logs" {
  rest_api_id   = aws_api_gateway_rest_api.logs.id
  resource_id   = aws_api_gateway_resource.logs.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_logs" {
  rest_api_id = aws_api_gateway_rest_api.logs.id
  resource_id = aws_api_gateway_resource.logs.id
  http_method = aws_api_gateway_method.options_logs.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "options_logs" {
  rest_api_id = aws_api_gateway_rest_api.logs.id
  resource_id = aws_api_gateway_resource.logs.id
  http_method = aws_api_gateway_method.options_logs.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_logs" {
  rest_api_id = aws_api_gateway_rest_api.logs.id
  resource_id = aws_api_gateway_resource.logs.id
  http_method = aws_api_gateway_method.options_logs.http_method
  status_code = aws_api_gateway_method_response.options_logs.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# --- Permissões para o API Gateway invocar as Lambdas ---
resource "aws_lambda_permission" "apigw_ingestion" {
  statement_id  = "AllowAPIGatewayInvokeIngestion"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.logs.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_query" {
  statement_id  = "AllowAPIGatewayInvokeQuery"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.logs.execution_arn}/*/*"
}

# --- Deployment + stage ---
resource "aws_api_gateway_deployment" "logs" {
  rest_api_id = aws_api_gateway_rest_api.logs.id

  # Redeploy quando qualquer parte da API mudar.
  triggers = {
    redeploy = sha1(jsonencode([
      aws_api_gateway_resource.logs.id,
      aws_api_gateway_method.post_logs.id,
      aws_api_gateway_integration.post_logs.id,
      aws_api_gateway_method.get_logs.id,
      aws_api_gateway_integration.get_logs.id,
      aws_api_gateway_method.options_logs.id,
      aws_api_gateway_integration.options_logs.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "logs" {
  rest_api_id   = aws_api_gateway_rest_api.logs.id
  deployment_id = aws_api_gateway_deployment.logs.id
  stage_name    = var.environment
}
