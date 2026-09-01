"""Pagamentos por pedido (VEN-003): entidade com valor/forma/taxa/provedor/status,
idempotência (retry não duplica), troco só em dinheiro, pendente não marca paga,
estorno reverte.
"""

from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories import caixa_repo

FORMAS = ("dinheiro", "pix", "cheque", "cartao_debito", "cartao_credito", "convenio", "boleto", "transferencia")
# formas que exigem confirmação externa antes de marcar a venda como paga
PENDENTES_POR_PADRAO = ("cartao_debito", "cartao_credito", "pix")


def registrar(orcamento_id: int, pagamentos: list[dict], idempotency_key: str | None = None,
              usuario_id: int | None = None) -> dict:
    """Registra os pagamentos do pedido (status pendente/confirmado)."""
    if not pagamentos:
        raise ValueError("pagamentos é obrigatório")
    with system_conn() as conn:
        orc = conn.execute("SELECT * FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone()
        if not orc:
            raise LookupError("Orçamento não encontrado")
        if orc["status"] not in ("finalizado", "recebido"):
            raise ValueError(f"Orçamento {orc['status']} — pagamentos exigem pedido finalizado")

        total = float(orc["total"] or 0)
        soma = 0.0
        criados = []
        pendentes = 0
        for i, p in enumerate(pagamentos):
            forma = (p.get("forma") or p.get("forma_pagamento") or "").strip().lower()
            if forma not in FORMAS:
                raise ValueError(f"forma de pagamento inválida: {forma}")
            valor = float(p.get("valor") or 0)
            if valor <= 0:
                raise ValueError("valor deve ser positivo")
            soma += valor
            key = f"{idempotency_key or 'auto'}-{i}" if idempotency_key else None
            status = "confirmado" if forma not in PENDENTES_POR_PADRAO else "pendente"
            if key:
                existente = conn.execute(
                    "SELECT id FROM orcamento_pagamento WHERE orcamento_id=? AND idempotency_key=?",
                    (orcamento_id, key),
                ).fetchone()
                if existente:
                    criados.append(existente["id"])
                    continue
            pid_novo = conn.execute(
                "INSERT INTO orcamento_pagamento (orcamento_id, forma, valor, taxa, provedor, bandeira,"
                " codigo_autorizacao, status, idempotency_key, confirmado_em)"
                " VALUES (?,?,?,?,?,?,?,?,?, CASE WHEN ? THEN NOW() ELSE NULL END) RETURNING id",
                (orcamento_id, forma, round(valor, 2), float(p.get("taxa") or 0),
                 p.get("provedor"), p.get("bandeira"), p.get("codigo_autorizacao"),
                 status, key, status == "confirmado"),
            ).fetchone()["id"]
            criados.append(pid_novo)
            if status == "confirmado":
                _lancar_caixa(conn, orc, forma, valor, p.get("bandeira"), p.get("codigo_autorizacao"), usuario_id)
            else:
                pendentes += 1
        if soma > total + 1e-6:
            tem_dinheiro = any((p.get("forma") or "").strip().lower() == "dinheiro" for p in pagamentos)
            if not tem_dinheiro:
                raise ValueError(f"Soma dos pagamentos ({soma:g}) excede o total da venda ({total:g}) — troco só em dinheiro")
            # com dinheiro, o excedente vira troco na confirmação
        # todas as formas confirmadas e soma fecha o total → venda paga
        if pendentes == 0 and soma >= total - 1e-6:
            conn.execute("UPDATE orcamentos SET status='recebido' WHERE id=?", (orcamento_id,))
        return {"orcamento_id": orcamento_id, "pagamentos": criados, "total": total,
                "total_pagamentos": round(soma, 2), "pendentes": pendentes}


def _lancar_caixa(conn, orc, forma, valor, bandeira, codigo, usuario_id):
    descricao = f"Venda {orc['numero']} — {orc['cliente'] or 'cliente'}"
    caixa_repo.movimentar(
        "entrada", descricao, round(valor, 2), forma_pagamento=forma,
        documento=orc["numero"], orcamento_id=orc["id"], usuario_id=usuario_id,
        bandeira=bandeira, codigo_autorizacao=codigo, _conn=conn,
    )


def confirmar(orcamento_id: int, idempotency_key: str | None = None, usuario_id: int | None = None) -> dict:
    """Confirma pagamentos pendentes (cartão/PIX) e marca a venda como paga quando
    a soma fecha o total (troco só em dinheiro)."""
    with system_conn() as conn:
        orc = conn.execute("SELECT * FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone()
        if not orc:
            raise LookupError("Orçamento não encontrado")
        total = float(orc["total"] or 0)
        pagamentos = conn.execute(
            "SELECT * FROM orcamento_pagamento WHERE orcamento_id=? ORDER BY id",
            (orcamento_id,),
        ).fetchall()
        if not pagamentos:
            raise ValueError("Nenhum pagamento registrado")
        soma_confirmado = 0.0
        troco = 0.0
        for p in pagamentos:
            if p["status"] == "estornado":
                continue
            if p["status"] == "pendente":
                conn.execute(
                    "UPDATE orcamento_pagamento SET status='confirmado', confirmado_em=NOW() WHERE id=?",
                    (p["id"],),
                )
                _lancar_caixa(conn, orc, p["forma"], float(p["valor"]), p["bandeira"], p["codigo_autorizacao"], usuario_id)
            soma_confirmado += float(p["valor"])
        # troco só em dinheiro: excedente devolvido como saída de caixa
        if soma_confirmado > total + 1e-6:
            troco = round(soma_confirmado - total, 2)
            dinheiro = next((p for p in pagamentos if p["forma"] == "dinheiro" and p["status"] != "estornado"), None)
            if dinheiro:
                caixa_repo.movimentar("saida", f"Troco venda {orc['numero']}", troco,
                                      forma_pagamento="dinheiro", orcamento_id=orcamento_id,
                                      usuario_id=usuario_id, _conn=conn)
            else:
                raise ValueError("Troco só é permitido em dinheiro")
        if soma_confirmado >= total - 1e-6:
            conn.execute("UPDATE orcamentos SET status='recebido' WHERE id=?", (orcamento_id,))
            pago = True
        else:
            pago = False
    return {"orcamento_id": orcamento_id, "total_pago": round(soma_confirmado, 2), "troco": troco,
            "pago": pago, "pendentes": _pendentes(orcamento_id)}


def estornar(pagamento_id: int, usuario_id: int | None = None) -> dict:
    """Estorna o pagamento: reverte o caixa e marca estornado."""
    with system_conn() as conn:
        p = conn.execute("SELECT * FROM orcamento_pagamento WHERE id=?", (pagamento_id,)).fetchone()
        if not p:
            raise LookupError("Pagamento não encontrado")
        if p["status"] == "estornado":
            return {"pagamento_id": pagamento_id, "duplicado": True}
        orc = conn.execute("SELECT * FROM orcamentos WHERE id=?", (p["orcamento_id"],)).fetchone()
        # reverte caixa se foi confirmado (saída)
        if p["status"] == "confirmado":
            caixa_repo.movimentar("saida", f"Estorno pagamento #{pagamento_id}", float(p["valor"]),
                                  forma_pagamento=p["forma"], orcamento_id=p["orcamento_id"],
                                  usuario_id=usuario_id, _conn=conn)
        conn.execute(
            "UPDATE orcamento_pagamento SET status='estornado', estornado_em=NOW() WHERE id=?",
            (pagamento_id,),
        )
        # se era o único e a venda estava recebida, volta para finalizado
        restantes = conn.execute(
            "SELECT COALESCE(SUM(valor),0) AS total_pago FROM orcamento_pagamento"
            " WHERE orcamento_id=? AND status IN ('pendente','confirmado')",
            (p["orcamento_id"],),
        ).fetchone()["total_pago"]
        if orc and orc["status"] == "recebido" and float(restantes or 0) < float(orc["total"] or 0):
            conn.execute("UPDATE orcamentos SET status='finalizado' WHERE id=?", (p["orcamento_id"],))
    return {"pagamento_id": pagamento_id, "status": "estornado"}


def _pendentes(orcamento_id: int) -> int:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM orcamento_pagamento WHERE orcamento_id=? AND status='pendente'",
            (orcamento_id,),
        ).fetchone()
    return int(row["count"])


def listar(orcamento_id: int) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM orcamento_pagamento WHERE orcamento_id=? ORDER BY id",
            (orcamento_id,),
        ).fetchall()]