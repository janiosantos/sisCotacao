"""Conciliação bancária (INT-001): importa extrato (normalizado), sugere matching
com contas por valor/documento/tolerância, aprova/rejeita com auditoria.
Extrato nunca cria baixa automática sem regra.
"""

from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import infra


def criar_conta(banco: str, agencia: str | None = None, conta: str | None = None) -> int:
    with system_conn() as conn:
        return conn.execute(
            "INSERT INTO conta_bancaria (banco, agencia, conta) VALUES (?,?,?) RETURNING id",
            (banco, (agencia or "").strip() or None, (conta or "").strip() or None),
        ).fetchone()["id"]


def importar_extrato(conta_id: int, movimentos: list[dict]) -> dict:
    """Importa movimentos do extrato (data, descricao, valor, documento).
    Idempotente por idempotencia_key; extrato não cria baixa automática."""
    from catalog_server.services.validacao import validar

    if not movimentos:
        raise ValueError("movimentos é obrigatório")
    schema_mov = {"data": {"tipo": "string", "requerido": True},
                  "valor": {"tipo": "float", "requerido": True},
                  "descricao": {"tipo": "string"},
                  "documento": {"tipo": "string"},
                  "idempotencia_key": {"tipo": "string"}}
    importados = 0
    with system_conn() as conn:
        for m in movimentos:
            erros, _ = validar(m or {}, schema_mov)
            if erros:
                raise ValueError(f"movimento inválido: {erros}")
            valor = float(m.get("valor") or 0)
            chave = m.get("idempotencia_key") or f"extrato-{conta_id}-{m.get('data')}-{m.get('documento') or m.get('descricao')}-{valor}"
            cur = conn.execute(
                "INSERT INTO extrato_bancario (conta_id, data, descricao, valor, documento, status, idempotencia_key)"
                " VALUES (?,?,?,?,?, 'importado', ?)"
                " ON CONFLICT (conta_id, idempotencia_key) DO NOTHING",
                (conta_id, str(m.get("data"))[:10], m.get("descricao"), valor,
                 m.get("documento"), chave),
            )
            importados += cur.rowcount
    return {"importados": importados}


def sugerir_matching(conta_id: int, tolerancia: float = 0.01) -> list[dict]:
    """Sugere correspondência extrato ↔ contas_receber/pagar por valor (tolerância)
    e documento. Aprovação é explícita."""
    with system_conn() as conn:
        movs = conn.execute(
            "SELECT * FROM extrato_bancario WHERE conta_id=? AND status IN ('importado','sugerido')",
            (conta_id,),
        ).fetchall()
        contas = [dict(c) | {"conta_tipo": "receber"} for c in conn.execute(
            """SELECT id, descricao, saldo, documento, data_vencimento, status
               FROM contas_receber WHERE status IN ('aberto','parcial')""",
        ).fetchall()] + [dict(c) | {"conta_tipo": "pagar"} for c in conn.execute(
            """SELECT id, descricao, saldo, documento, data_vencimento, status
               FROM contas_pagar WHERE status IN ('aberto','parcial')""",
        ).fetchall()]
        sugestoes = []
        for m in movs:
            melhor = None
            for c in contas:
                if abs(float(m["valor"] or 0) - abs(float(c["saldo"] or 0))) <= tolerancia:
                    melhor = c
                    break
            if melhor:
                conn.execute(
                    "UPDATE extrato_bancario SET status='sugerido', matching_conta_id=?, "
                    "matching_conta_tipo=? WHERE id=?",
                    (melhor["id"], melhor["conta_tipo"], m["id"]),
                )
                sugestoes.append({"movimento_id": m["id"], "matching_conta_id": melhor["id"],
                                  "matching_conta_tipo": melhor["conta_tipo"],
                                  "valor": float(m["valor"] or 0), "descricao": m["descricao"],
                                  "conta_descricao": melhor["descricao"]})
    return sugestoes


def aprovar(movimento_id: int, usuario_id: int | None = None) -> dict:
    """Aprova a conciliação: baixa a conta correspondente e marca conciliado (auditado)."""
    with system_conn() as conn:
        mov = conn.execute("SELECT * FROM extrato_bancario WHERE id=? FOR UPDATE", (movimento_id,)).fetchone()
        if not mov:
            raise LookupError("Movimento bancário não encontrado")
        if mov["status"] == "conciliado":
            return {"movimento_id": movimento_id, "duplicado": True}
        conta = None
        conta_tipo = mov["matching_conta_tipo"]
        if mov["matching_conta_id"] and conta_tipo in ("receber", "pagar"):
            tabela = "contas_receber" if conta_tipo == "receber" else "contas_pagar"
            conta = conn.execute(
                f"SELECT * FROM {tabela} WHERE id=? FOR UPDATE", (mov["matching_conta_id"],)
            ).fetchone()
        elif mov["matching_conta_id"]:
            # Compatibilidade com sugestões gravadas antes da coluna de tipo:
            # só aceita quando o ID existir em exatamente um ledger.
            receber = conn.execute(
                "SELECT * FROM contas_receber WHERE id=? FOR UPDATE", (mov["matching_conta_id"],)
            ).fetchone()
            pagar = conn.execute(
                "SELECT * FROM contas_pagar WHERE id=? FOR UPDATE", (mov["matching_conta_id"],)
            ).fetchone()
            if receber and pagar:
                raise ValueError("Conciliação ambígua: informe o tipo do título")
            conta = receber or pagar
            conta_tipo = "receber" if receber else "pagar" if pagar else None
        if mov["matching_conta_id"] and conta is None:
            raise ValueError("Título da conciliação não encontrado")
        if conta:
            if float(conta["saldo"] or 0) <= 0 or conta["status"] == "pago":
                raise ValueError("Título já baixado ou sem saldo")
            if abs(abs(float(mov["valor"] or 0)) - float(conta["saldo"] or 0)) > 0.01:
                raise ValueError("Valor do extrato diverge do saldo do título")
            if conta_tipo == "receber":
                conn.execute(
                    "UPDATE contas_receber SET status='pago', data_recebimento=NOW(), saldo=0 WHERE id=?",
                    (mov["matching_conta_id"],),
                )
            else:
                conn.execute(
                    "UPDATE contas_pagar SET status='pago', data_pagamento=NOW(), saldo=0 WHERE id=?",
                    (mov["matching_conta_id"],),
                )
        conn.execute(
            "UPDATE extrato_bancario SET status='conciliado', aprovado_por=?, aprovado_em=NOW(), "
            "matching_conta_tipo=? WHERE id=?",
            (usuario_id, conta_tipo, movimento_id),
        )
        infra.registrar("conciliar_bancario", "extrato_bancario", movimento_id,
                        depois={"status": "conciliado", "matching": mov["matching_conta_id"],
                                "matching_tipo": conta_tipo},
                        ator_id=usuario_id, conn=conn)
    return {"movimento_id": movimento_id, "status": "conciliado", "conta_baixada": bool(conta)}


def rejeitar(movimento_id: int, usuario_id: int | None = None) -> dict:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE extrato_bancario SET status='rejeitado', matching_conta_id=NULL, "
            "matching_conta_tipo=NULL, aprovado_por=? WHERE id=?",
            (usuario_id, movimento_id),
        )
        if cur.rowcount == 0:
            raise LookupError("Movimento bancário não encontrado")
    return {"movimento_id": movimento_id, "status": "rejeitado"}


def listar(conta_id: int, status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM extrato_bancario WHERE conta_id=?"
    args: list = [conta_id]
    if status:
        sql += " AND status=?"
        args.append(status)
    sql += " ORDER BY id DESC LIMIT 500"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]
