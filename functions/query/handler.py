"""Lambda de query (GET /logs). Placeholder — lê do DynamoDB."""

import json


def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"items": [], "count": 0, "placeholder": True}),
    }
