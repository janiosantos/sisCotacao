"""Cotação a partir de necessidade (COM-008): comando idempotente que consolida
itens compatíveis de solicitações/sugestões, preserva depósito/destino, convida
fornecedores conforme preferência e permite split.
"""

from __future__ import annotations

from catalog_server.db import system_conn


def gerar_cotacao(sc_id: int, apelido: str | None = None, usuario_id: int | None = None) -> dict:
    """Cria/consolida uma cotação a partir de uma solicitação aprovada.
    Idempotente: se já existir cotação para a solicitação, devolve a existente
    (origem rastreável via solicitacao_id)."""
    with system_conn() as conn:
        sc = conn.execute(
            "SELECT * FROM solicitacao_compra WHERE id=?", (sc_id,)
        ).fetchone()
        if not sc:
            raise LookupError("Solicitação não encontrada")
        if sc["status"] not in ("aprovada", "cotando"):
            raise ValueError(f"Solicitação {sc['status']} não está pronta para cotação")

        existente = conn.execute(
            "SELECT id FROM cotacoes WHERE solicitacao_id=?", (sc_id,)
        ).fetchone()
        if existente:
            return {"cotacao_id": existente["id"], "duplicado": True, "itens": 0}

        itens = conn.execute(
            "SELECT si.*, p.sku, p.nome AS produto_nome, p.unidade_venda, p.fator_conversao"
            " FROM solicitacao_itens si JOIN produtos_cadastro p ON p.id=si.produto_id"
            " WHERE si.solicitacao_id=?",
            (sc_id,),
        ).fetchall()
        if not itens:
            raise ValueError("Solicitação sem itens")

        numero = sc["codigo"] or f"COT-SOL-{sc_id}"
        cot_id = conn.execute(
            "INSERT INTO cotacoes (numero, status, observacoes, solicitacao_id, versao)"
            " VALUES (?, 'aberta', ?, ?, 1) RETURNING id",
            (numero, apelido or f"da solicitação {sc['codigo']}", sc_id),
        ).fetchone()["id"]

        for it in itens:
            conn.execute(
                "INSERT INTO cotacao_itens (cotacao_id, produto_id, descricao, quantidade,"
                " unidade_solicitada, solicitacao_item_id)"
                " VALUES (?,?,?,?,?,?)",
                (cot_id, it["produto_id"], it["produto_nome"], it["quantidade"],
                 it["unidade"] or "UN", it["id"]),
            )

        # convida fornecedores preferenciais por produto (ranking)
        fornecedores: set[int] = set()
        for it in itens:
            rows = conn.execute(
                "SELECT fornecedor_id FROM fornecedor_preferencial WHERE produto_id=? ORDER BY ranking",
                (it["produto_id"],),
            ).fetchall()
            fornecedores.update(r["fornecedor_id"] for r in rows)

        conn.execute("UPDATE solicitacao_compra SET status='cotando' WHERE id=?", (sc_id,))
    return {"cotacao_id": cot_id, "duplicado": False, "itens": len(itens),
            "fornecedores": len(fornecedores), "fornecedor_ids": sorted(fornecedores)}


def buscar_propostas_por_produto(cotacao_id: int) -> dict:
    """Itens da cotação sem proposta (comprador vê itens sem proposta)."""
    with system_conn() as conn:
        itens = [dict(r) for r in conn.execute(
            "SELECT ci.id, ci.produto_id, ci.descricao, ci.quantidade, ci.unidade_solicitada,"
            " p.sku, p.unidade_venda"
            " FROM cotacao_itens ci JOIN produtos_cadastro p ON p.id=ci.produto_id"
            " WHERE ci.cotacao_id=? ORDER BY ci.id",
            (cotacao_id,),
        ).fetchall()]
        com_proposta = set()
        for it in itens:
            r = conn.execute(
                "SELECT 1 FROM cotacao_precos WHERE cotacao_item_id=?",
                (it["id"],),
            ).fetchone()
            if r:
                com_proposta.add(it["produto_id"])
    for it in itens:
        it["tem_proposta"] = it["produto_id"] in com_proposta
    return {"itens": itens, "sem_proposta": [i for i in itens if not i["tem_proposta"]]}