"""Teste local da Lambda processadora, sem AWS.

Mocka o boto3/DynamoDB e simula um evento SQS em batch com logs
válidos e inválidos, verificando validação, TTL e batchItemFailures.

Uso: python scripts/test_processor.py
"""

import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "functions" / "layer" / "python"))
sys.path.insert(0, str(ROOT / "functions" / "processor"))

# --- Mock do boto3 antes de importar o handler ---
written_items = []


class _FakeTable:
    def put_item(self, Item):
        written_items.append(Item)


class _FakeResource:
    def Table(self, name):
        return _FakeTable()


fake_boto3 = types.ModuleType("boto3")
fake_boto3.resource = lambda service: _FakeResource()
sys.modules["boto3"] = fake_boto3

os.environ["TABLE_NAME"] = "logs-dev"
os.environ["TTL_DAYS"] = "30"

import handler  # noqa: E402
from log_schema import validate_log  # noqa: E402


def sqs_event(bodies):
    return {
        "Records": [
            {"messageId": f"m{i}", "body": json.dumps(b) if isinstance(b, dict) else b}
            for i, b in enumerate(bodies)
        ]
    }


def main():
    valido = {
        "service": "auth-service",
        "level": "ERROR",
        "message": "falha no login",
        "timestamp": "2026-09-12T16:00:00Z",
        "trace_id": "abc-123",
    }
    sem_service = {"level": "INFO", "message": "x", "timestamp": "2026-09-12T16:00:00Z"}
    level_ruim = {**valido, "level": "DEBUG"}
    ts_ruim = {**valido, "timestamp": "ontem"}
    nao_json = "isso não é json"

    # 1) Validação unitária
    assert validate_log(valido) == [], "válido deveria passar"
    assert any("service" in e for e in validate_log(sem_service))
    assert any("level" in e for e in validate_log(level_ruim))
    assert any("timestamp" in e for e in validate_log(ts_ruim))
    print("[ok] validate_log cobre válido, campo ausente, level e timestamp inválidos")

    # 2) Handler em batch
    event = sqs_event([valido, sem_service, level_ruim, ts_ruim, nao_json])
    result = handler.handler(event, None)

    failures = {f["itemIdentifier"] for f in result["batchItemFailures"]}
    assert failures == {"m1", "m2", "m3", "m4"}, f"falhas inesperadas: {failures}"
    print(f"[ok] batchItemFailures = {sorted(failures)} (apenas os inválidos)")

    assert len(written_items) == 1, f"esperava 1 item gravado, gravou {len(written_items)}"
    item = written_items[0]
    assert item["service"] == "auth-service"
    assert item["timestamp"] == "2026-09-12T16:00:00Z"
    assert item["trace_id"] == "abc-123"
    # TTL: 2026-09-12T16:00:00Z em epoch + 30 dias
    esperado_ttl = 1789228800 + 30 * 86400
    assert item["expire_at"] == esperado_ttl, f"TTL={item['expire_at']} != {esperado_ttl}"
    print(f"[ok] item gravado com PK/SK corretos e expire_at={item['expire_at']}")

    print("\nTodos os testes passaram.")


if __name__ == "__main__":
    main()
