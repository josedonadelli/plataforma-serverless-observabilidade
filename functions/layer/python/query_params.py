"""Parsing/validação dos parâmetros de busca do GET /logs e cursor de paginação.

Puro (sem boto3), para ser testável localmente e reusável.
"""

import base64
import json

from log_schema import VALID_LEVELS, parse_timestamp

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def parse_query(params):
    """Valida a query string e retorna (parsed, errors).

    parsed: {service, level?, start_time?, end_time?, limit, cursor?}
    errors: lista de mensagens (vazia se válido).
    """
    params = params or {}
    errors = []
    parsed = {}

    service = params.get("service")
    if not service:
        errors.append("parâmetro obrigatório ausente: service")
    else:
        parsed["service"] = service

    level = params.get("level")
    if level is not None:
        if level in VALID_LEVELS:
            parsed["level"] = level
        else:
            errors.append(f"level inválido: {level} (use {sorted(VALID_LEVELS)})")

    for field in ("start_time", "end_time"):
        value = params.get(field)
        if value is not None:
            try:
                parse_timestamp(value)
                parsed[field] = value
            except ValueError:
                errors.append(f"{field} não é ISO 8601 válido: {value}")

    if "start_time" in parsed and "end_time" in parsed:
        if parsed["start_time"] > parsed["end_time"]:
            errors.append("start_time não pode ser maior que end_time")

    limit = params.get("limit")
    if limit is None:
        parsed["limit"] = DEFAULT_LIMIT
    else:
        try:
            n = int(limit)
            if n < 1 or n > MAX_LIMIT:
                errors.append(f"limit deve estar entre 1 e {MAX_LIMIT}")
            else:
                parsed["limit"] = n
        except (TypeError, ValueError):
            errors.append(f"limit inválido: {limit}")

    cursor = params.get("cursor")
    if cursor:
        try:
            parsed["cursor"] = decode_cursor(cursor)
        except (ValueError, json.JSONDecodeError):
            errors.append("cursor inválido")

    return parsed, errors


def encode_cursor(last_evaluated_key):
    """Serializa o LastEvaluatedKey do DynamoDB em um cursor opaco (base64)."""
    if not last_evaluated_key:
        return None
    raw = json.dumps(last_evaluated_key, sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor):
    """Reverte encode_cursor -> dict para usar como ExclusiveStartKey."""
    raw = base64.urlsafe_b64decode(cursor.encode())
    return json.loads(raw)
