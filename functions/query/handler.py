"""Lambda de query (GET /logs).

Consulta o DynamoDB por service + intervalo de timestamp (KeyCondition),
filtra por level (FilterExpression) e pagina via cursor opaco.
"""

import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

from query_params import encode_cursor, parse_query

TABLE_NAME = os.environ["TABLE_NAME"]

_table = boto3.resource("dynamodb").Table(TABLE_NAME)

_CORS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


def _json_default(value):
    # DynamoDB devolve números como Decimal; converte para int/float.
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"não serializável: {type(value).__name__}")


def _response(status, body):
    body_json = json.dumps(body, default=_json_default)
    return {"statusCode": status, "headers": _CORS, "body": body_json}


def _build_key_condition(parsed):
    """KeyConditionExpression: service + intervalo de timestamp (SK)."""
    cond = Key("service").eq(parsed["service"])
    start, end = parsed.get("start_time"), parsed.get("end_time")
    if start and end:
        cond &= Key("timestamp").between(start, end)
    elif start:
        cond &= Key("timestamp").gte(start)
    elif end:
        cond &= Key("timestamp").lte(end)
    return cond


def handler(event, context):
    parsed, errors = parse_query(event.get("queryStringParameters"))
    if errors:
        return _response(400, {"errors": errors})

    kwargs = {
        "KeyConditionExpression": _build_key_condition(parsed),
        "Limit": parsed["limit"],
    }
    if "level" in parsed:
        kwargs["FilterExpression"] = Attr("level").eq(parsed["level"])
    if "cursor" in parsed:
        kwargs["ExclusiveStartKey"] = parsed["cursor"]

    result = _table.query(**kwargs)
    items = result.get("Items", [])

    return _response(200, {
        "items": items,
        "count": len(items),
        "next_cursor": encode_cursor(result.get("LastEvaluatedKey")),
    })
