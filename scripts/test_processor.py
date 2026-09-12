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
metric_calls = []


class _FakeTable:
    def put_item(self, Item):
        written_items.append(Item)


class _FakeResource:
    def Table(self, name):
        return _FakeTable()


class _FakeCloudWatch:
    def put_metric_data(self, Namespace, MetricData):
        metric_calls.append({"Namespace": Namespace, "MetricData": MetricData})


fake_boto3 = types.ModuleType("boto3")
fake_boto3.resource = lambda service: _FakeResource()
fake_boto3.client = lambda service: _FakeCloudWatch()
sys.modules["boto3"] = fake_boto3

os.environ["TABLE_NAME"] = "logs-dev"
os.environ["TTL_DAYS"] = "30"
os.environ["METRIC_NAMESPACE"] = "LogsPlatform"

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

    # 3) Métrica de ERROR: 1 log ERROR gravado -> 1 PutMetricData com Value 1
    assert len(metric_calls) == 1, f"esperava 1 PutMetricData, houve {len(metric_calls)}"
    call = metric_calls[0]
    assert call["Namespace"] == "LogsPlatform"
    datum = call["MetricData"][0]
    assert datum["MetricName"] == "ErrorLogs"
    assert datum["Value"] == 1, f"contagem de ERROR={datum['Value']} != 1"
    print(f"[ok] métrica ErrorLogs publicada com Value={datum['Value']}")

    # 4) Batch sem ERROR não publica métrica
    metric_calls.clear()
    so_info = {**valido, "level": "INFO"}
    handler.handler(sqs_event([so_info]), None)
    assert metric_calls == [], "batch sem ERROR não deveria publicar métrica"
    print("[ok] batch sem ERROR não publica métrica")

    print("\nTodos os testes passaram.")


if __name__ == "__main__":
    main()
