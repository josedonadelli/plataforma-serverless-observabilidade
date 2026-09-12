"""Teste local das rotas POST /logs e GET /logs (lógica pura, sem AWS).

- ingestão: validação + publicação na SQS (boto3 mockado) + resposta 202/400
- query_params: parsing/validação da query string e cursor

Uso: python scripts/test_api.py
"""

import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "functions" / "layer" / "python"))
sys.path.insert(0, str(ROOT / "functions" / "ingestion"))

# --- Mock do boto3 (client SQS) antes de importar a ingestão ---
sent_messages = []


class _FakeSqs:
    def send_message(self, QueueUrl, MessageBody):
        sent_messages.append(MessageBody)
        return {"MessageId": "fake"}


fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = lambda service: _FakeSqs()
sys.modules["boto3"] = fake_boto3

import os  # noqa: E402

os.environ["QUEUE_URL"] = "https://sqs.local/queue"


def test_ingestion():
    import handler as ing

    # válido -> 202 + trace_id, publica na fila
    body = {
        "service": "auth-service",
        "level": "INFO",
        "message": "login ok",
        "timestamp": "2026-09-12T16:00:00Z",
    }
    resp = ing.handler({"body": json.dumps(body)}, None)
    assert resp["statusCode"] == 202, resp
    payload = json.loads(resp["body"])
    assert payload["trace_id"], "deveria gerar trace_id"
    assert len(sent_messages) == 1
    assert json.loads(sent_messages[0])["trace_id"] == payload["trace_id"]
    print("[ok] POST válido -> 202, trace_id gerado e mensagem publicada na SQS")

    # inválido -> 400, não publica
    resp = ing.handler({"body": json.dumps({"level": "INFO"})}, None)
    assert resp["statusCode"] == 400, resp
    assert len(sent_messages) == 1, "não deveria publicar inválido"
    print("[ok] POST inválido -> 400 e nada publicado")

    # body não-JSON -> 400
    resp = ing.handler({"body": "xxx"}, None)
    assert resp["statusCode"] == 400
    print("[ok] POST body não-JSON -> 400")


def test_query_params():
    from query_params import decode_cursor, encode_cursor, parse_query

    # service obrigatório
    _, errors = parse_query({})
    assert any("service" in e for e in errors)

    # válido com filtros
    parsed, errors = parse_query({
        "service": "auth",
        "level": "ERROR",
        "start_time": "2026-09-12T00:00:00Z",
        "end_time": "2026-09-12T23:59:59Z",
        "limit": "10",
    })
    assert errors == [], errors
    assert parsed["service"] == "auth" and parsed["level"] == "ERROR"
    assert parsed["limit"] == 10

    # level e limit inválidos
    _, errors = parse_query({"service": "auth", "level": "DEBUG", "limit": "0"})
    assert any("level" in e for e in errors)
    assert any("limit" in e for e in errors)

    # intervalo invertido
    _, errors = parse_query({
        "service": "auth",
        "start_time": "2026-09-12T10:00:00Z",
        "end_time": "2026-09-12T09:00:00Z",
    })
    assert any("start_time" in e for e in errors)

    # cursor roundtrip
    key = {"service": "auth", "timestamp": "2026-09-12T10:00:00Z"}
    parsed, errors = parse_query({"service": "auth", "cursor": encode_cursor(key)})
    assert errors == [] and parsed["cursor"] == key
    assert decode_cursor(encode_cursor(key)) == key
    print("[ok] parse_query cobre obrigatório, filtros, inválidos, intervalo e cursor")


if __name__ == "__main__":
    test_ingestion()
    test_query_params()
    print("\nTodos os testes passaram.")
