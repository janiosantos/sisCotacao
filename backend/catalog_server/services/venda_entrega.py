"""Retirada e entrega da venda (VEN-005): separa balcão/entrega com estados
pendente → enviada → entregue e auditoria de endereço/data.
"""

from __future__ import annotations

from catalog_server.db import system_conn

_TRANSICOES: dict[str, set[str]] = {
    "pendente": {"enviada"},   # entrega exige envio; balcão usa retirar()
    "enviada": {"entregue"},
    "entregue": set(),
}


def configurar_entrega(orcamento_id: int, tipo_entrega: str, endereco: str | None = None,
                       data_entrega: str | None = None) -> dict:
    tipo = (tipo_entrega or "balcao").strip().lower()
    if tipo not in ("balcao", "entrega"):
        raise ValueError("tipo_entrega inválido (balcao|entrega)")
    with system_conn() as conn:
        row = conn.execute("SELECT status FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone()
        if not row:
            raise LookupError("Orçamento não encontrado")
        if row["status"] not in ("finalizado", "recebido"):
            raise ValueError(f"Orçamento {row['status']} — configure a entrega apenas após finalizar")
        if tipo == "entrega" and not (endereco or "").strip():
            raise ValueError("endereco de entrega é obrigatório")
        conn.execute(
            "UPDATE orcamentos SET tipo_entrega=?, status_entrega='pendente', endereco_entrega=?, data_entrega=?"
            " WHERE id=?",
            (tipo, (endereco or "").strip() or None, data_entrega, orcamento_id),
        )
    return {"orcamento_id": orcamento_id, "tipo_entrega": tipo, "status_entrega": "pendente"}


def transicionar(orcamento_id: int, novo_status: str) -> dict:
    novo_status = (novo_status or "").strip().lower()
    if novo_status not in ("enviada", "entregue"):
        raise ValueError("status_entrega inválido (enviada|entregue)")
    with system_conn() as conn:
        row = conn.execute(
            "SELECT tipo_entrega, status_entrega FROM orcamentos WHERE id=?", (orcamento_id,)
        ).fetchone()
        if not row:
            raise LookupError("Orçamento não encontrado")
        atual = row["status_entrega"]
        if novo_status not in _TRANSICOES.get(atual, set()):
            raise ValueError(f"Transição inválida: {atual} → {novo_status}")
        if novo_status == "enviada" and row["tipo_entrega"] != "entrega":
            raise ValueError("Apenas entregas podem ser enviadas (balcão retira direto)")
        conn.execute(
            "UPDATE orcamentos SET status_entrega=? WHERE id=?", (novo_status, orcamento_id)
        )
    return {"orcamento_id": orcamento_id, "de": atual, "para": novo_status}


def retirar(orcamento_id: int) -> dict:
    """Retirada no balcão: pendente → entregue direto."""
    with system_conn() as conn:
        row = conn.execute(
            "SELECT tipo_entrega, status_entrega FROM orcamentos WHERE id=?", (orcamento_id,)
        ).fetchone()
        if not row:
            raise LookupError("Orçamento não encontrado")
        if row["tipo_entrega"] != "balcao":
            raise ValueError("Apenas vendas de balcão podem ser retiradas direto")
        conn.execute(
            "UPDATE orcamentos SET status_entrega='entregue' WHERE id=?", (orcamento_id,)
        )
    return {"orcamento_id": orcamento_id, "status_entrega": "entregue"}


def listar(status: str | None = None) -> list[dict]:
    sql = (
        "SELECT o.id, o.numero, o.cliente, o.cliente_id, o.tipo_entrega, o.status_entrega,"
        " o.endereco_entrega, o.data_entrega, o.total, o.status AS venda_status"
        " FROM orcamentos o"
    )
    args: list = []
    if status:
        sql += " WHERE o.status_entrega=?"
        args.append(status)
    sql += " ORDER BY o.id DESC LIMIT 200"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]