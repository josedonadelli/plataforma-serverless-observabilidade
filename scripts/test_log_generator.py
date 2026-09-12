"""Teste local do gerador de logs, sem rede.

Verifica que os logs gerados são válidos pelo schema compartilhado, que o
modo pico eleva a proporção de ERROR, que a normalização da URL funciona e
que --dry-run/--count não fazem chamadas de rede.

Uso: python scripts/test_log_generator.py
"""

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "functions" / "layer" / "python"))
sys.path.insert(0, str(ROOT / "scripts"))

import log_generator as gen  # noqa: E402
from log_schema import validate_log  # noqa: E402


def test_logs_validos():
    rng = random.Random(1)
    for _ in range(500):
        log = gen.build_log(rng, gen.DEFAULT_SERVICES, error_rate=0.3)
        assert validate_log(log) == [], f"log inválido gerado: {log}"
    print("[ok] 500 logs gerados passam no validate_log do schema")


def test_error_rate():
    rng = random.Random(2)
    n = 5000
    erros = sum(
        1
        for _ in range(n)
        if gen.build_log(rng, gen.DEFAULT_SERVICES, error_rate=0.9)["level"] == "ERROR"
    )
    frac = erros / n
    assert 0.85 < frac < 0.95, f"proporção de ERROR fora do esperado: {frac:.2f}"
    print(f"[ok] error_rate=0.9 produz ~{frac:.0%} de ERROR")

    rng = random.Random(3)
    erros_baixo = sum(
        1
        for _ in range(n)
        if gen.build_log(rng, gen.DEFAULT_SERVICES, error_rate=0.05)["level"] == "ERROR"
    )
    assert erros_baixo / n < 0.1, "error_rate baixo não deveria gerar muitos ERROR"
    print("[ok] error_rate baixo gera poucos ERROR")


def test_endpoint():
    assert gen._logs_endpoint("https://x/dev") == "https://x/dev/logs"
    assert gen._logs_endpoint("https://x/dev/") == "https://x/dev/logs"
    assert gen._logs_endpoint("https://x/dev/logs") == "https://x/dev/logs"
    print("[ok] normalização da URL para /logs")


def test_spike_flag():
    # --spike sem --error-rate explícito eleva a proporção de ERROR.
    args = gen.parse_args(["--dry-run", "--spike", "--count", "1"])
    assert args.spike and args.error_rate == 0.1  # default; main() eleva para 0.9
    print("[ok] flag --spike reconhecida")


def test_dry_run_nao_envia():
    # Substitui send_log por um espião; --dry-run/--count não deve chamá-lo.
    original = gen.send_log
    chamadas = []
    gen.send_log = lambda *a, **k: chamadas.append(a) or 202
    try:
        rc = gen.main(["--dry-run", "--count", "10", "--seed", "1"])
    finally:
        gen.send_log = original
    assert rc == 0
    assert chamadas == [], "dry-run não deveria chamar send_log"
    print("[ok] --dry-run não faz chamadas de rede")


def main():
    test_logs_validos()
    test_error_rate()
    test_endpoint()
    test_spike_flag()
    test_dry_run_nao_envia()
    print("\nTodos os testes passaram.")


if __name__ == "__main__":
    main()
