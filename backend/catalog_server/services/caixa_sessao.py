"""Sessão de caixa e terminal (VEN-004): abertura, suprimento, sangria,
fechamento com diferença e aprovação. Fechamento bloqueia novos movimentos.
"""

from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories import caixa_repo


def abrir(operador_id: int, saldo_inicial: float, deposito_id: int = 1, terminal: str | None = None) -> dict:
    saldo_inicial = float(saldo_inicial or 0)
    if saldo_inicial < 0:
        raise ValueError("saldo_inicial não pode ser negativo")
    with system_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM caixa_sessao WHERE operador_id=? AND status='aberta'",
            (operador_id,),
        ).fetchone()
        if existente:
            raise ValueError("Operador já possui sessão de caixa aberta")
        sessao_id = conn.execute(
            "INSERT INTO caixa_sessao (deposito_id, operador_id, terminal, saldo_inicial, status)"
            " VALUES (?,?,?,?, 'aberta') RETURNING id",
            (deposito_id, operador_id, terminal, saldo_inicial),
        ).fetchone()["id"]
        if saldo_inicial > 0:
            caixa_repo.movimentar(
                "abertura", f"Abertura de caixa (sessão #{sessao_id})", saldo_inicial,
                usuario_id=operador_id, sessao_id=sessao_id, _conn=conn,
            )
    return {"sessao_id": sessao_id, "operador_id": operador_id, "status": "aberta", "saldo_inicial": saldo_inicial}


def _validar_aberta(conn, sessao_id: int) -> dict:
    sess = conn.execute("SELECT * FROM caixa_sessao WHERE id=?", (sessao_id,)).fetchone()
    if not sess:
        raise LookupError("Sessão de caixa não encontrada")
    if sess["status"] != "aberta":
        raise ValueError(f"Sessão {sess['status']} — não aceita movimentos")
    return dict(sess)


def suprimento(sessao_id: int, valor: float, descricao: str = "", usuario_id: int | None = None) -> dict:
    with system_conn() as conn:
        sess = _validar_aberta(conn, sessao_id)
        r = caixa_repo.movimentar(
            "suprimento", descricao or f"Suprimento (sessão #{sessao_id})", float(valor),
            usuario_id=usuario_id or sess["operador_id"], sessao_id=sessao_id, _conn=conn,
        )
    return r


def sangria(sessao_id: int, valor: float, descricao: str = "", usuario_id: int | None = None) -> dict:
    with system_conn() as conn:
        sess = _validar_aberta(conn, sessao_id)
        r = caixa_repo.movimentar(
            "sangria", descricao or f"Sangria (sessão #{sessao_id})", float(valor),
            usuario_id=usuario_id or sess["operador_id"], sessao_id=sessao_id, _conn=conn,
        )
    return r


def fechar(sessao_id: int, saldo_contado: float, justificativa: str | None = None) -> dict:
    saldo_contado = float(saldo_contado or 0)
    with system_conn() as conn:
        sess = _validar_aberta(conn, sessao_id)
        movs = conn.execute(
            "SELECT tipo, valor FROM caixa_movimento WHERE sessao_id=?",
            (sessao_id,),
        ).fetchall()
        esperado = float(sess["saldo_inicial"] or 0)
        for m in movs:
            if m["tipo"] in ("entrada", "suprimento"):
                esperado += float(m["valor"] or 0)
            elif m["tipo"] in ("saida", "sangria"):
                esperado -= float(m["valor"] or 0)
        diferenca = round(saldo_contado - esperado, 2)
        conn.execute(
            "UPDATE caixa_sessao SET status='fechada', fechamento_em=NOW(), saldo_esperado=?,"
            " saldo_contado=?, diferenca=?, justificativa=? WHERE id=?",
            (round(esperado, 2), saldo_contado, diferenca, justificativa, sessao_id),
        )
    return {"sessao_id": sessao_id, "status": "fechada", "saldo_esperado": round(esperado, 2),
            "saldo_contado": saldo_contado, "diferenca": diferenca}


def aprovar(sessao_id: int, aprovador_id: int) -> dict:
    with system_conn() as conn:
        sess = conn.execute("SELECT status FROM caixa_sessao WHERE id=?", (sessao_id,)).fetchone()
        if not sess:
            raise LookupError("Sessão de caixa não encontrada")
        if sess["status"] != "fechada":
            raise ValueError("Aprovação de diferença exige sessão fechada")
        conn.execute(
            "UPDATE caixa_sessao SET aprovador_id=?, aprovado_em=NOW() WHERE id=?",
            (aprovador_id, sessao_id),
        )
    return {"sessao_id": sessao_id, "aprovador_id": aprovador_id, "aprovado": True}


def detalhe(sessao_id: int) -> dict | None:
    with system_conn() as conn:
        sess = conn.execute(
            "SELECT s.*, u.nome AS operador_nome, d.nome AS deposito_nome"
            " FROM caixa_sessao s"
            " LEFT JOIN usuarios u ON u.id=s.operador_id"
            " LEFT JOIN depositos d ON d.id=s.deposito_id WHERE s.id=?",
            (sessao_id,),
        ).fetchone()
        if not sess:
            return None
        movs = [dict(r) for r in conn.execute(
            "SELECT * FROM caixa_movimento WHERE sessao_id=? ORDER BY id",
            (sessao_id,),
        ).fetchall()]
        out = dict(sess)
        out["movimentos"] = movs
        return out


def listar(status: str | None = None, operador_id: int | None = None) -> list[dict]:
    sql = (
        "SELECT s.*, u.nome AS operador_nome FROM caixa_sessao s"
        " LEFT JOIN usuarios u ON u.id=s.operador_id"
    )
    args: list = []
    where: list[str] = []
    if status:
        where.append("s.status=?")
        args.append(status)
    if operador_id:
        where.append("s.operador_id=?")
        args.append(operador_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY s.id DESC LIMIT 50"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]