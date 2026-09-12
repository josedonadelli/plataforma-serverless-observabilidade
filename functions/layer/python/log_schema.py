"""Schema e validação do log, compartilhados entre as Lambdas via layer.

Contrato do log:
    service    (str, obrigatório)  — origem do log
    level      (str, obrigatório)  — INFO | WARN | ERROR
    message    (str, obrigatório)  — texto do evento
    timestamp  (str, obrigatório)  — ISO 8601 (ex.: 2026-09-12T16:00:00Z)
    trace_id   (str, opcional)     — correlação entre eventos
"""

from datetime import datetime, timezone

VALID_LEVELS = {"INFO", "WARN", "ERROR"}
REQUIRED_STR_FIELDS = ("service", "level", "message", "timestamp")


def parse_timestamp(value):
    """Converte um timestamp ISO 8601 em datetime tz-aware (UTC se sem offset).

    Levanta ValueError se o formato for inválido.
    """
    # fromisoformat não aceita o sufixo 'Z'; normaliza para +00:00.
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def validate_log(payload):
    """Valida o payload do log e retorna uma lista de erros (vazia se válido)."""
    errors = []

    if not isinstance(payload, dict):
        return ["payload deve ser um objeto JSON"]

    for field in REQUIRED_STR_FIELDS:
        value = payload.get(field)
        if value is None or value == "":
            errors.append(f"campo obrigatório ausente: {field}")
        elif not isinstance(value, str):
            errors.append(f"campo {field} deve ser string")

    level = payload.get("level")
    if isinstance(level, str) and level not in VALID_LEVELS:
        errors.append(f"level inválido: {level} (use {sorted(VALID_LEVELS)})")

    timestamp = payload.get("timestamp")
    if isinstance(timestamp, str) and timestamp:
        try:
            parse_timestamp(timestamp)
        except ValueError:
            errors.append(f"timestamp não é ISO 8601 válido: {timestamp}")

    trace_id = payload.get("trace_id")
    if trace_id is not None and not isinstance(trace_id, str):
        errors.append("trace_id deve ser string")

    return errors
