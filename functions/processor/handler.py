"""Lambda processadora: consome mensagens da SQS em batch e persiste no DynamoDB.

Mensagens inválidas ou que falham a escrita são reportadas como batchItemFailures,
fazendo a SQS reentregá-las (e, após maxReceiveCount, encaminhá-las à DLQ).
"""

import json
import os

import boto3

from log_schema import parse_timestamp, validate_log

TABLE_NAME = os.environ["TABLE_NAME"]
TTL_DAYS = int(os.environ.get("TTL_DAYS", "30"))

_table = boto3.resource("dynamodb").Table(TABLE_NAME)


def build_item(log):
    """Monta o item do DynamoDB a partir de um log já validado."""
    expire_at = int(parse_timestamp(log["timestamp"]).timestamp()) + TTL_DAYS * 86400
    item = {
        "service": log["service"],
        "timestamp": log["timestamp"],
        "level": log["level"],
        "message": log["message"],
        "expire_at": expire_at,
    }
    if log.get("trace_id"):
        item["trace_id"] = log["trace_id"]
    return item


def handler(event, context):
    failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId")
        try:
            log = json.loads(record["body"])
        except (json.JSONDecodeError, KeyError):
            print(f"[{message_id}] body não é JSON válido")
            failures.append({"itemIdentifier": message_id})
            continue

        errors = validate_log(log)
        if errors:
            print(f"[{message_id}] log inválido: {errors}")
            failures.append({"itemIdentifier": message_id})
            continue

        try:
            _table.put_item(Item=build_item(log))
        except Exception as exc:  # falha de escrita -> reentrega
            print(f"[{message_id}] falha ao gravar no DynamoDB: {exc}")
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
