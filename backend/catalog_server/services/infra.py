"""Idempotência transversal (ARC-003) e auditoria de eventos (ARC-006)."""

from __future__ import annotations

import hashlib
import json

from catalog_server.db import system_conn


# ─── ARC-003: Idempotência central ─────────────────────────

def executar(chave: str, escopo: str, payload, fn, conn=None) -> dict:
    """Executa `fn` uma única vez por `chave`+escopo. Retry devolve o resultado
    anterior; chave reutilizada com payload diferente é rejeitada."""
    chave = (chave or "").strip()
    if not chave:
        raise ValueError("chave idempotente é obrigatória")
    payload_hash = hashlib.sha1(json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True).encode()).hexdigest()
    conn_externo = conn is not None
    ctx = None if conn_externo else system_conn()
    conn2 = conn or ctx.__enter__()
    try:
        existente = conn2.execute(
            "SELECT payload_hash, resultado FROM idempotencia WHERE chave=? AND escopo=?",
            (chave, escopo),
        ).fetchone()
        if existente:
            if existente["payload_hash"] != payload_hash:
                raise ValueError(f"Chave idempotente {chave} reutilizada com payload diferente")
            return {"duplicado": True, "resultado": existente["resultado"]}
        resultado = fn(conn2)
        conn2.execute(
            "INSERT INTO idempotencia (chave, escopo, payload_hash, resultado)"
            " VALUES (?,?,?,?) ON CONFLICT (chave) DO NOTHING",
            (chave, escopo, payload_hash, json.dumps(resultado, ensure_ascii=False, default=str)),
        )
        if not conn_externo:
            conn2.commit()
        return {"duplicado": False, "resultado": resultado}
    finally:
        if not conn_externo and ctx is not None:
            ctx.__exit__(None, None, None)


# ─── ARC-006: Auditoria de eventos ─────────────────────────

def registrar(acao: str, alvo_tipo: str | None = None, alvo_id=None, antes: dict | None = None,
              depois: dict | None = None, motivo: str | None = None, ator_id: int | None = None,
              ator_login: str | None = None, ip: str | None = None, correlation_id: str | None = None,
              conn=None) -> None:
    """Registra evento de negócio. `antes/depois` são mascarados (LGPD) antes de gravar."""
    if conn is None:
        with system_conn() as c:
            _insert_auditoria(c, acao, alvo_tipo, alvo_id, antes, depois, motivo,
                              ator_id, ator_login, ip, correlation_id)
    else:
        _insert_auditoria(conn, acao, alvo_tipo, alvo_id, antes, depois, motivo,
                          ator_id, ator_login, ip, correlation_id)


def _insert_auditoria(conn, acao, alvo_tipo, alvo_id, antes, depois, motivo,
                      ator_id, ator_login, ip, correlation_id) -> None:
    import json
    import catalog_server.services.lgpd as lgpd
    conn.execute(
        "INSERT INTO auditoria_evento (ator_id, ator_login, acao, alvo_tipo, alvo_id, antes, depois,"
        " motivo, ip, correlation_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (ator_id, (ator_login or "").strip() or None, (acao or "").strip(), alvo_tipo,
         str(alvo_id) if alvo_id is not None else None,
         json.dumps(lgpd.mascarar_dict(antes), ensure_ascii=False) if antes else None,
         json.dumps(lgpd.mascarar_dict(depois), ensure_ascii=False) if depois else None,
         (motivo or "").strip() or None, ip, correlation_id),
    )


def listar(alvo_tipo: str | None = None, alvo_id=None, limite: int = 200) -> list[dict]:
    sql = "SELECT * FROM auditoria_evento"
    args: list = []
    where: list[str] = []
    if alvo_tipo:
        where.append("alvo_tipo=?")
        args.append(alvo_tipo)
    if alvo_id is not None:
        where.append("alvo_id=?")
        args.append(str(alvo_id))
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limite)
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]