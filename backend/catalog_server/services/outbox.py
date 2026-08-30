"""Outbox transacional (P5).

Operações assíncronas confiáveis: a linha é gravada junto do fato de negócio
(na mesma transação), e o worker RQ processa com retry/backoff, dead-letter e
idempotência por chave.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from catalog_server.db import system_conn

MAX_TENTATIVAS = 5
BACKOFF_BASE_SEG = 60  # 1min, 2min, 4min, 8min (expoente)


def enfileirar(topico: str, payload: dict, chave_idempotencia: str = "") -> int:
    """Grava uma operação no outbox. Idempotente por `chave_idempotencia`."""
    texto = json.dumps(payload, ensure_ascii=False, default=str)
    with system_conn() as conn:
        if chave_idempotencia:
            existe = conn.execute(
                "SELECT 1 FROM outbox WHERE idempotencia_key=?", (chave_idempotencia,)
            ).fetchone()
            if existe:
                return int(conn.execute(
                    "SELECT id FROM outbox WHERE idempotencia_key=?", (chave_idempotencia,)
                ).fetchone()[0])
        cur = conn.execute(
            "INSERT INTO outbox (topico, payload, status, idempotencia_key)"
            " VALUES (?,?, 'pendente', ?) RETURNING id",
            (topico, texto, chave_idempotencia or None),
        )
        row = cur.fetchone()
        conn.commit()
        return int(row[0])


def prontas(limite: int = 50) -> list[dict]:
    """Linhas pendentes prontas para processar (agora ou atrasadas)."""
    agora = datetime.now(timezone.utc)
    with system_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM outbox
               WHERE status='pendente' AND (proxima_tentativa IS NULL OR proxima_tentativa <= ?)
               ORDER BY id LIMIT ?""",
            (agora, limite),
        ).fetchall()
    return [dict(r) for r in rows]


def pendentes_contagem() -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE status='pendente'"
        ).fetchone()["n"])


def marcar_ok(outbox_id: int) -> None:
    with system_conn() as conn:
        conn.execute(
            "UPDATE outbox SET status='ok', atualizado_em=NOW() WHERE id=?", (outbox_id,)
        )
        conn.commit()


def marcar_erro(outbox_id: int, erro: str) -> None:
    """Incrementa tentativas; agenda backoff; morta após MAX_TENTATIVAS."""
    with system_conn() as conn:
        row = conn.execute("SELECT tentativas FROM outbox WHERE id=?", (outbox_id,)).fetchone()
        if row is None:
            return
        tentativas = int(row[0]) + 1
        if tentativas >= MAX_TENTATIVAS:
            conn.execute(
                "UPDATE outbox SET status='morta', tentativas=?, ultimo_erro=?, atualizado_em=NOW()"
                " WHERE id=?",
                (tentativas, erro[:500], outbox_id),
            )
        else:
            atraso = BACKOFF_BASE_SEG * (2 ** (tentativas - 1))
            prox = datetime.now(timezone.utc) + timedelta(seconds=atraso)
            conn.execute(
                "UPDATE outbox SET status='pendente', tentativas=?, ultimo_erro=?,"
                " proxima_tentativa=?, atualizado_em=NOW() WHERE id=?",
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