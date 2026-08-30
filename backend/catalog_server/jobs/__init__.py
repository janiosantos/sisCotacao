"""Processamento assíncrono (P5) — fila RQ + Redis.

Tarefas de segundo plano executadas por um worker RQ separado do web:
- `rechecagem`: consulta o provedor das cobranças pendentes e baixa as pagas
  (cobre webhooks perdidos/falhos). Agendada periodicamente pelo scheduler.
- (futuro) outbox transacional para webhooks/imagens/integrações.
"""
from __future__ import annotations

import os

from redis import Redis


def _redis() -> Redis:
    return Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


def enfileirar(func: str, *args, timeout: int = 120, **kwargs) -> None:
    """Enfileira uma tarefa RQ pelo caminho de import (ex.: catalog_server.jobs.tasks.rechecagem)."""
    from rq import Queue

    Queue("default", connection=_redis()).enqueue(func, *args, timeout=timeout, **kwargs)