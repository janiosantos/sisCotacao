"""Outbox transacional (P5).

Operações assíncronas confiáveis: a linha é gravada junto do fato de negócio
(na mesma transação), e o worker RQ processa com retry/backoff, dead-letter e
idempotência por chave.
"""
from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timedelta, timezone

from catalog_server.db import system_conn

MAX_TENTATIVAS = 5
BACKOFF_BASE_SEG = 60  # 1min, 2min, 4min, 8min (expoente)
LEASE_MINUTOS = 10


def enfileirar(topico: str, payload: dict, chave_idempotencia: str = "") -> int:
    """Grava uma operação no outbox. Idempotente por `chave_idempotencia`."""
    texto = json.dumps(payload, ensure_ascii=False, default=str)
    with system_conn() as conn:
        if chave_idempotencia:
            # INSERT ... ON CONFLICT elimina a janela SELECT -> INSERT entre
            # duas requisições concorrentes com a mesma chave.
            cur = conn.execute(
                "INSERT INTO outbox (topico, payload, status, idempotencia_key)"
                " VALUES (?,?, 'pendente', ?)"
                " ON CONFLICT (idempotencia_key) DO UPDATE"
                " SET idempotencia_key=EXCLUDED.idempotencia_key RETURNING id",
                (topico, texto, chave_idempotencia),
            )
        else:
            cur = conn.execute(
                "INSERT INTO outbox (topico, payload, status, idempotencia_key)"
                " VALUES (?,?, 'pendente', NULL) RETURNING id",
                (topico, texto),
            )
        row = cur.fetchone()
        conn.commit()
        return int(row[0])


def prontas(limite: int = 50) -> list[dict]:
    """Reivindica linhas prontas para processamento exclusivo deste worker."""
    limite = max(1, min(500, int(limite)))
    worker = f"{socket.gethostname()}:{os.getpid()}"
    with system_conn() as conn:
        # Um worker morto não pode bloquear a fila para sempre. O lease é
        # maior que o timeout das tarefas RQ e só recupera linhas abandonadas.
        conn.execute(
            "UPDATE outbox SET status='pendente', processando_em=NULL, processando_por=NULL "
            "WHERE status='processando' AND processando_em < NOW() - interval '10 minutes'"
        )
        rows = conn.execute(
            """WITH candidatos AS (
                   SELECT id FROM outbox
                   WHERE status='pendente'
                     AND (proxima_tentativa IS NULL OR proxima_tentativa <= NOW())
                   ORDER BY id
                   FOR UPDATE SKIP LOCKED
                   LIMIT ?
               )
               UPDATE outbox AS o
                  SET status='processando', processando_em=NOW(), processando_por=?
                 FROM candidatos c
                WHERE o.id=c.id
               RETURNING o.*""",
            (limite, worker),
        ).fetchall()
        conn.commit()
    return [dict(r) for r in rows]


def pendentes_contagem() -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE status IN ('pendente','processando')"
        ).fetchone()["n"])


def marcar_ok(outbox_id: int) -> None:
    with system_conn() as conn:
        conn.execute(
            "UPDATE outbox SET status='ok', processando_em=NULL, processando_por=NULL,"
            " atualizado_em=NOW() WHERE id=? AND status='processando'", (outbox_id,)
        )
        conn.commit()


def marcar_erro(outbox_id: int, erro: str) -> None:
    """Incrementa tentativas; agenda backoff; morta após MAX_TENTATIVAS."""
    with system_conn() as conn:
        row = conn.execute(
            "SELECT tentativas FROM outbox WHERE id=? FOR UPDATE", (outbox_id,)
        ).fetchone()
        if row is None:
            return
        tentativas = int(row[0]) + 1
        if tentativas >= MAX_TENTATIVAS:
            conn.execute(
                "UPDATE outbox SET status='morta', tentativas=?, ultimo_erro=?, atualizado_em=NOW()"
                ", processando_em=NULL, processando_por=NULL WHERE id=?",
                (tentativas, erro[:500], outbox_id),
            )
        else:
            atraso = BACKOFF_BASE_SEG * (2 ** (tentativas - 1))
            prox = datetime.now(timezone.utc) + timedelta(seconds=atraso)
            conn.execute(
                "UPDATE outbox SET status='pendente', tentativas=?, ultimo_erro=?,"
                " proxima_tentativa=?, processando_em=NULL, processando_por=NULL,"
                " atualizado_em=NOW() WHERE id=?",
                (tentativas, erro[:500], prox, outbox_id),
            )
        conn.commit()


def listar(status: str = "", limite: int = 50) -> list[dict]:
    with system_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM outbox WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limite),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM outbox ORDER BY id DESC LIMIT ?", (limite,)
            ).fetchall()
    return [dict(r) for r in rows]
