"""Lambda de ingestão (POST /logs). Placeholder — publica na fila SQS."""

import json


def handler(event, context):
    return {
        "statusCode": 202,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "accepted", "placeholder": True}),
    }
