"""Lambda de ingestão (POST /logs).

Valida o corpo (reusa log_schema do layer), publica na fila SQS e responde 202.
"""

import json
import os
import uuid

import boto3

from log_schema import validate_log

QUEUE_URL = os.environ["QUEUE_URL"]

_sqs = boto3.client("sqs")

_CORS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


def _response(status, body):
    return {"statusCode": status, "headers": _CORS, "body": json.dumps(body)}


def handler(event, context):
    raw = event.get("body") or ""
    try:
        log = json.loads(raw)
    except json.JSONDecodeError:
        return _response(400, {"errors": ["corpo não é JSON válido"]})

    errors = validate_log(log)
    if errors:
        return _response(400, {"errors": errors})

    # Garante um trace_id para correlação, gerando um se o cliente não enviar.
    trace_id = log.get("trace_id") or str(uuid.uuid4())
    log["trace_id"] = trace_id

    _sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(log))

    return _response(202, {"status": "accepted", "trace_id": trace_id})
