"""Scheduler — agenda tarefas periódicas na fila RQ.

- a cada `OUTBOX_INTERVAL_SEC` (default 60) enfileira o processamento do outbox;
- a cada `RECHECAGEM_INTERVAL_MIN` (default 15) enfileira a rechecagem em lotes.
Encerra limpo em SIGTERM.
"""
from __future__ import annotations

import os
import signal
import time

from catalog_server.jobs import _redis, enfileirar


def _intervalo_rechecagem() -> int:
    return max(1, int(os.getenv("RECHECAGEM_INTERVAL_MIN", "15")))


def _intervalo_outbox() -> int:
    return max(10, int(os.getenv("OUTBOX_INTERVAL_SEC", "60")))


def main() -> None:
    intervalo_outbox = _intervalo_outbox()
    intervalo_rechecagem = _intervalo_rechecagem()
    print(f"scheduler: outbox a cada {intervalo_outbox}s; rechecagem a cada {intervalo_rechecagem}min")
    _redis().ping()
    parar = False

    def _stop(*_):
        nonlocal parar
        parar = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    tick = 0
    ticks_por_rechecagem = max(1, (intervalo_rechecagem * 60) // intervalo_outbox)
    while not parar:
        try:
            enfileirar("catalog_server.jobs.tasks.rodar_outbox", timeout=120)
            print("scheduler: outbox enfileirado")
        except Exception as exc:
            print(f"scheduler: falha ao enfileirar outbox: {exc}")
        if tick % ticks_por_rechecagem == 0:
            try:
                enfileirar("catalog_server.jobs.tasks.rechecagem", timeout=300)
                print("scheduler: rechecagem enfileirada")
            except Exception as exc:
                print(f"scheduler: falha ao enfileirar rechecagem: {exc}")
        tick += 1
        time.sleep(intervalo_outbox)


if __name__ == "__main__":
    main()