"""Gerador de logs simulados para a plataforma de logs.

Gera logs de serviços fictícios com níveis variados e envia via POST /logs.
Suporta três cenários:

  * fluxo contínuo  — taxa (logs/s) por uma duração, ou uma contagem fixa;
  * pico de erros   — eleva a proporção de ERROR para disparar o alarme (--spike);
  * volume/rajada   — alto volume concorrente para observar fila/DLQ (--burst).

Usa apenas a biblioteca padrão (urllib). O contrato do log é o mesmo do
layer compartilhado; o trace_id é gerado pela ingestão, então não é enviado.

Exemplos:
  python scripts/log_generator.py --url https://xxxx.execute-api.sa-east-1.amazonaws.com/dev --rate 5 --duration 10
  python scripts/log_generator.py --url <base> --spike --count 30
  python scripts/log_generator.py --url <base> --burst 500 --concurrency 20
"""

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

DEFAULT_SERVICES = [
    "auth-service",
    "payment-service",
    "order-service",
    "inventory-service",
    "notification-service",
]

# Mensagens por nível para dar variedade realista ao corpo do log.
MESSAGES = {
    "INFO": [
        "requisição processada com sucesso",
        "usuário autenticado",
        "cache atualizado",
        "job agendado concluído",
    ],
    "WARN": [
        "latência acima do esperado",
        "tentativa de retry",
        "conexão lenta com dependência",
        "uso de memória elevado",
    ],
    "ERROR": [
        "falha ao conectar no banco",
        "timeout na dependência externa",
        "exceção não tratada",
        "pagamento recusado pelo provedor",
    ],
}


def choose_level(error_rate, rng):
    """Escolhe um nível. ERROR com probabilidade error_rate; o resto vira
    INFO/WARN numa proporção 4:1."""
    if rng.random() < error_rate:
        return "ERROR"
    return "INFO" if rng.random() < 0.8 else "WARN"


def build_log(rng, services, error_rate, now=None):
    """Monta um log válido (dict) conforme o contrato compartilhado."""
    now = now or datetime.now(timezone.utc)
    level = choose_level(error_rate, rng)
    # Precisão de milissegundos reduz colisões de sort key (timestamp) em rajada.
    timestamp = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {
        "service": rng.choice(services),
        "level": level,
        "message": rng.choice(MESSAGES[level]),
        "timestamp": timestamp,
    }


def send_log(url, log, timeout=10):
    """Envia um log via POST. Retorna o status HTTP (ou 0 em falha de rede)."""
    data = json.dumps(log).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError as exc:
        print(f"falha de rede: {exc.reason}", file=sys.stderr)
        return 0


def _logs_endpoint(base_url):
    """Normaliza a URL para terminar em /logs."""
    base = base_url.rstrip("/")
    return base if base.endswith("/logs") else base + "/logs"


def _new_stats():
    return {"sent": 0, "error_logs": 0, "accepted": 0, "statuses": {}}


def _record(stats, status):
    """Contabiliza um envio: 202 conta como aceito; guarda a distribuição."""
    stats["statuses"][status] = stats["statuses"].get(status, 0) + 1
    if status == 202:
        stats["accepted"] += 1


def run_stream(url, rng, services, error_rate, rate, duration, count, dry_run):
    """Envia logs em fluxo: `count` mensagens, ou por `duration` s à taxa `rate`."""
    interval = 1.0 / rate if rate > 0 else 0
    total = count if count is not None else None
    deadline = None if total is not None else time.monotonic() + duration

    sent = 0
    stats = _new_stats()
    while True:
        if total is not None and sent >= total:
            break
        if deadline is not None and time.monotonic() >= deadline:
            break

        log = build_log(rng, services, error_rate)
        stats["sent"] += 1
        if log["level"] == "ERROR":
            stats["error_logs"] += 1

        if dry_run:
            print(json.dumps(log))
            stats["accepted"] += 1
        else:
            _record(stats, send_log(url, log))

        sent += 1
        if interval and not (total is not None and sent >= total):
            time.sleep(interval)
    return stats


def run_burst(url, rng, services, error_rate, count, concurrency, dry_run):
    """Envia `count` logs o mais rápido possível usando `concurrency` threads."""
    logs = [build_log(rng, services, error_rate) for _ in range(count)]
    stats = _new_stats()
    stats["sent"] = count
    stats["error_logs"] = sum(1 for lg in logs if lg["level"] == "ERROR")
    if dry_run:
        for lg in logs:
            print(json.dumps(lg))
        stats["accepted"] = count
        return stats

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(send_log, url, lg) for lg in logs]
        for fut in as_completed(futures):
            _record(stats, fut.result())
    return stats


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Gerador de logs simulados (POST /logs).")
    p.add_argument("--url", help="URL base da API (ex.: https://.../dev) ou .../logs")
    p.add_argument("--rate", type=float, default=5.0, help="logs por segundo (fluxo)")
    p.add_argument("--duration", type=float, default=10.0, help="duração em s (fluxo)")
    p.add_argument("--count", type=int, help="número fixo de logs (ignora --duration)")
    p.add_argument(
        "--error-rate",
        type=float,
        default=0.1,
        help="proporção de logs ERROR (0..1)",
    )
    p.add_argument(
        "--spike",
        action="store_true",
        help="cenário de pico: eleva ERROR para 0.9 (se --error-rate não for dado)",
    )
    p.add_argument(
        "--burst",
        type=int,
        metavar="N",
        help="cenário de volume: envia N logs concorrentes o mais rápido possível",
    )
    p.add_argument("--concurrency", type=int, default=20, help="threads no modo --burst")
    p.add_argument("--seed", type=int, help="semente para reprodutibilidade")
    p.add_argument("--dry-run", action="store_true", help="imprime os logs, não envia")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if not 0.0 <= args.error_rate <= 1.0:
        print("--error-rate deve estar entre 0 e 1", file=sys.stderr)
        return 2
    if not args.dry_run and not args.url:
        print("--url é obrigatório (ou use --dry-run)", file=sys.stderr)
        return 2

    # No pico, se o usuário não escolheu explicitamente uma taxa, sobe para 0.9.
    error_rate = args.error_rate
    if args.spike and args.error_rate == 0.1:
        error_rate = 0.9

    rng = random.Random(args.seed)
    url = _logs_endpoint(args.url) if args.url else None

    if args.burst is not None:
        stats = run_burst(
            url, rng, DEFAULT_SERVICES, error_rate, args.burst, args.concurrency, args.dry_run
        )
    else:
        stats = run_stream(
            url, rng, DEFAULT_SERVICES, error_rate, args.rate, args.duration, args.count, args.dry_run
        )

    verbo = "gerados" if args.dry_run else "aceitos (202)"
    print(
        f"\nEnviados: {stats['sent']} | {verbo}: {stats['accepted']} | "
        f"ERROR: {stats['error_logs']}"
    )
    # Distribuição de status quando houve resposta diferente de 202
    # (0 = falha de rede). Útil para flagrar throttling/erros sob carga.
    outros = {s: n for s, n in stats.get("statuses", {}).items() if s != 202}
    if outros:
        detalhe = ", ".join(f"HTTP {s}: {n}" for s, n in sorted(outros.items()))
        print(f"Respostas não-202: {detalhe}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
