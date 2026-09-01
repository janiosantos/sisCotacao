"""Pedido de compra (COM-011): gerar pedido dos vencedores, máquina de estados e
cancelamento. (COM-012): histórico de preço/prazo/desempenho por produto/fornecedor.
"""

from __future__ import annotations

from catalog_server.db import system_conn


# ─── COM-011: pedido a partir dos vencedores ───────────────

_TRANSICOES: dict[str, set[str]] = {
    "rascunho": {"aprovado", "cancelado"},
    "aprovado": {"enviado", "cancelado"},
    "enviado": {"confirmado", "cancelado"},
    "confirmado": {"parcialmente_recebido", "recebido"},
    "parcialmente_recebido": {"parcialmente_recebido", "recebido"},
    "recebido": set(),
    "cancelado": set(),
}


def gerar_pedido(cotacao_id: int, usuario_id: int | None = None) -> dict:
    """Gera um pedido por fornecedor vencedor da cotação (status rascunho)."""
    with system_conn() as conn:
        cot = conn.execute("SELECT * FROM cotacoes WHERE id=?", (cotacao_id,)).fetchone()
        if not cot:
            raise LookupError("Cotação não encontrada")
        if not cot["decisao_concluida"]:
            raise ValueError("Cotação sem decisão concluída (defina os vencedores)")
        vencedores = conn.execute(
            "SELECT cp.*, ci.id AS cotacao_item_id, ci.produto_id, ci.quantidade, ci.unidade_solicitada"
            " FROM cotacao_precos cp JOIN cotacao_itens ci ON ci.id=cp.cotacao_item_id"
            " WHERE cp.vencedor AND ci.cotacao_id=?",
            (cotacao_id,),
        ).fetchall()
        if not vencedores:
            raise ValueError("Nenhum vencedor definido")

        pedidos = []
        por_fornecedor: dict[int, list] = {}
        for v in vencedores:
            por_fornecedor.setdefault(v["fornecedor_id"], []).append(v)
        for fid, itens in por_fornecedor.items():
            numero = f"PC-{cotacao_id}-{fid}"
            pedido_id = conn.execute(
                "INSERT INTO pedidos_compra (numero, cotacao_id, fornecedor_id, status, data_pedido)"
                " VALUES (?,?,?, 'rascunho', NOW()) RETURNING id",
                (numero, cotacao_id, fid),
            ).fetchone()["id"]
            for it in itens:
                conn.execute(
                    "INSERT INTO pedido_itens (cotacao_id, cotacao_item_id, pedido_id, fornecedor_id,"
                    " preco_unitario, quantidade)"
                    " VALUES (?,?,?,?,?,?)",
                    (cotacao_id, it["cotacao_item_id"], pedido_id, fid,
                     it["preco_unitario"], it["quantidade"]),
                )
            pedidos.append(pedido_id)
    return {"pedidos": pedidos, "fornecedores": len(pedidos), "itens": len(vencedores)}


def transicionar(pedido_id: int, novo_status: str, usuario_id: int | None = None) -> dict:
    novo_status = (novo_status or "").strip().lower()
    with system_conn() as conn:
        row = conn.execute("SELECT status FROM pedidos_compra WHERE id=?", (pedido_id,)).fetchone()
        if not row:
            raise LookupError("Pedido não encontrado")
        atual = row["status"]
        if novo_status not in _TRANSICOES.get(atual, set()):
            raise ValueError(f"Transição inválida: {atual} → {novo_status}")
        conn.execute("UPDATE pedidos_compra SET status=? WHERE id=?", (novo_status, pedido_id))
    return {"id": pedido_id, "de": atual, "para": novo_status}


def cancelar(pedido_id: int, motivo: str | None = None) -> dict:
    """Cancela o pedido se ainda não recebido (saldo cancelado não recebe)."""
    with system_conn() as conn:
        row = conn.execute("SELECT status FROM pedidos_compra WHERE id=?", (pedido_id,)).fetchone()
        if not row:
            raise LookupError("Pedido não encontrado")
        if row["status"] == "cancelado":
            return {"id": pedido_id, "de": "cancelado", "para": "cancelado", "duplicado": True}
        if row["status"] in ("recebido", "parcialmente_recebido"):
            raise ValueError(f"Pedido {row['status']} não pode ser cancelado")
        conn.execute(
            "UPDATE pedidos_compra SET status='cancelado', observacoes=CASE"
            " WHEN CAST(? AS TEXT) IS NULL THEN observacoes"
            " ELSE COALESCE(observacoes,'') || ' | cancelado: ' || CAST(? AS TEXT) END WHERE id=?",
            (motivo, motivo, pedido_id),
        )
    return {"id": pedido_id, "de": row["status"], "para": "cancelado"}


def pode_receber(pedido_id: int) -> bool:
    with system_conn() as conn:
        row = conn.execute("SELECT status FROM pedidos_compra WHERE id=?", (pedido_id,)).fetchone()
    return bool(row and row["status"] in ("enviado", "confirmado", "parcialmente_recebido"))


# ─── COM-012: histórico de preço/prazo por produto/fornecedor ─


def historico_produto(produto_id: int) -> dict:
    with system_conn() as conn:
        precos = [dict(r) for r in conn.execute(
            """
            SELECT pc.numero AS pedido, pc.data_pedido, pc.status, f.nome AS fornecedor,
                   pi.preco_unitario, pi.quantidade, pi.fornecedor_id
            FROM pedido_itens pi
            JOIN pedidos_compra pc ON pc.id=pi.pedido_id
            JOIN fornecedores f ON f.id=pi.fornecedor_id
            JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id
            WHERE ci.produto_id=?
            ORDER BY pc.data_pedido DESC, pc.id DESC LIMIT 50
            """,
            (produto_id,),
        ).fetchall()]
        preferenciais = [dict(r) for r in conn.execute(
            "SELECT f.nome AS fornecedor, fp.ranking, fp.ultimo_preco, fp.ultimo_prazo"
            " FROM fornecedor_preferencial fp JOIN fornecedores f ON f.id=fp.fornecedor_id"
            " WHERE fp.produto_id=? ORDER BY fp.ranking",
            (produto_id,),
        ).fetchall()]
    return {"produto_id": produto_id, "precos": precos, "preferenciais": preferenciais}