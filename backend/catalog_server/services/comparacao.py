"""Comparação de propostas (COM-009): custo efetivo (preço líquido + impostos do
motor fiscal) e decisão de vencedor com justificativa. Não escolhe só pelo menor
preço — o usuário decide e justifica.
"""

from __future__ import annotations

from catalog_server.db import system_conn


def custo_efetivo(preco_liquido: float, aliquota_icms: float = 0, aliquota_pis: float = 0,
                  aliquota_cofins: float = 0, frete: float = 0) -> float:
    """Custo efetivo: preço líquido + impostos (por dentro) + frete unitário."""
    imposto = aliquota_icms + aliquota_pis + aliquota_cofins
    base = preco_liquido / (1 - imposto / 100.0) if imposto < 100 else preco_liquido
    return round(base + frete, 4)


def montar_comparacao(cotacao_id: int) -> dict:
    """Matriz por item com custo efetivo por fornecedor (usa motor fiscal p/ impostos)."""
    from catalog_server.services.compras import montar_matriz

    matriz = montar_matriz(cotacao_id)
    if matriz is None:
        raise LookupError("Cotação não encontrada")
    for it in matriz.get("itens", []):
        produto_id = it.get("produto_id")
        icms = pis = cofins = 0.0
        if produto_id:
            try:
                from catalog_server.services import custo_engine

                c = custo_engine.calcular_custo(produto_id)
                if c:
                    icms = float(c.get("icms", 0) or 0)
                    pis = float(c.get("pis", 0) or 0)
                    cofins = float(c.get("cofins", 0) or 0)
            except Exception:  # noqa: BLE001 (motor indisponível → sem impostos)
                pass
        it["impostos"] = {"icms": icms, "pis": pis, "cofins": cofins}
        for fid, pr in (it.get("precos") or {}).items():
            liquido = float(pr["preco_liquido"])
            pr["custo_efetivo"] = custo_efetivo(liquido, icms, pis, cofins)
    return matriz


def decidir_vencedor(preco_id: int, justificativa: str, usuario_id: int | None = None) -> dict:
    """Marca o vencedor de um item (preco_id) e limpa os demais da mesma cotacao_item."""
    justificativa = (justificativa or "").strip()
    if not justificativa:
        raise ValueError("justificativa é obrigatória")
    with system_conn() as conn:
        alvo = conn.execute(
            "SELECT id, cotacao_item_id FROM cotacao_precos WHERE id=?",
            (preco_id,),
        ).fetchone()
        if not alvo:
            raise LookupError("Proposta não encontrada")
        conn.execute(
            "UPDATE cotacao_precos SET vencedor=FALSE WHERE cotacao_item_id=?",
            (alvo["cotacao_item_id"],),
        )
        conn.execute(
            "UPDATE cotacao_precos SET vencedor=TRUE, justificativa_vencedor=?,"
            " data_decisao=NOW(), decidido_por=? WHERE id=?",
            (justificativa, usuario_id, preco_id),
        )
        # conclui se todos os itens da cotação tiverem vencedor
        cot_item = conn.execute(
            "SELECT ci.cotacao_id FROM cotacao_itens ci JOIN cotacao_precos cp ON cp.cotacao_item_id=ci.id"
            " WHERE ci.id=?", (alvo["cotacao_item_id"],),
        ).fetchone()
        if cot_item:
            sem = conn.execute(
                "SELECT COUNT(*) FROM cotacao_itens ci"
                " WHERE ci.cotacao_id=? AND NOT EXISTS (SELECT 1 FROM cotacao_precos cp"
                "   WHERE cp.cotacao_item_id=ci.id AND cp.vencedor)",
                (cot_item["cotacao_id"],),
            ).fetchone()["count"]
            if sem == 0:
                conn.execute(
                    "UPDATE cotacoes SET decisao_concluida=TRUE WHERE id=?",
                    (cot_item["cotacao_id"],),
                )
    return {"preco_id": preco_id, "vencedor": True, "justificativa": justificativa}