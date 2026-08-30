"""Scheduler — agenda tarefas periódicas na fila RQ.

Loop simples: a cada `RECHECAGEM_INTERVAL_MIN` (default 15) enfileira a
rechecagem. Encerra limpo em SIGTERM.
"""
from __future__ import annotations

import os
import signal
import time

from catalog_server.jobs import _redis, enfileirar


def _intervalo() -> int:
    return max(1, int(os.getenv("RECHECAGEM_INTERVAL_MIN", "15")))


def main() -> None:
    intervalo = _intervalo()
    print(f"scheduler: rechecagem a cada {intervalo} min")
    _redis().ping()
    parar = False

    def _stop(*_):
        nonlocal parar
        parar = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while not parar:
        try:
            enfileirar("catalog_server.jobs.tasks.rechecagem", timeout=300)
            print("scheduler: rechecagem enfileirada")
        except Exception as exc:
            print(f"scheduler: falha ao enfileirar rechecagem: {exc}")
        time.sleep(intervalo * 60)


if __name__ == "__main__":
    main()