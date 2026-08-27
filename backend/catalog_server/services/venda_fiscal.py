"""Snapshot fiscal da venda (FASE 8).

Para cada item de um orçamento, monta o contexto fiscal (produto + destino) e
grava o `FiscalResult` em `orcamento_itens_fiscal`. A validação usa os erros
"hard" (NCM, CFOP, CST/CSOSN) para decidir se a venda pode ser finalizada —
contexto de destino incompleto (UF/contribuinte/modelo) fica como WARNING nesta
etapa, até o coletor de contexto no PDV/NFC-e (FASE 9).

O snapshot garante reprodução histórica: se a regra mudar amanhã, a nota emitida
ontem continua usando o cálculo gravado.
"""
from __future__ import annotations

import json

from catalog_server.db import system_conn
from catalog_server.repositories.orcamentos import orcamento_repo
from catalog_server.services import fiscal_motor

# Erros que impedem a finalização (bloqueiam a emissão).
CAMPOS_BLOQUEANTES = {"ncm", "cfop", "cst_icms", "csosn"}

_COLS = (
    "data_operacao", "regime", "ncm", "cest", "cfop", "origem",
    "cst_icms", "csosn", "cst_pis", "cst_cofins", "cst_ibs", "cst_cbs",
    "aliquota_icms", "base_icms", "valor_icms",
    "modalidade_st", "base_icms_st", "aliquota_icms_st", "valor_icms_st",
    "aliquota_pis", "valor_pis", "aliquota_cofins", "valor_cofins",
    "aliquota_ibs", "valor_ibs", "aliquota_cbs", "valor_cbs",
)


def snapshot_orcamento(orcamento_id: int) -> dict | None:
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return None

    dados = {
        "operacao": "venda",
        "uf_destino": orc.get("uf_destino"),
        "tipo_cliente": orc.get("tipo_cliente"),
        "contribuinte": orc.get("contribuinte"),
        "modelo_documento": orc.get("modelo_documento"),
        "data": (orc.get("criado_em") or "")[:10],
    }
    # Contexto do destino: completa a partir do cliente vinculado (se faltar)
    if orc.get("cliente_id"):
        with system_conn() as conn:
            cli = conn.execute(
                "SELECT tipo_pessoa, uf, contribuinte, ie FROM clientes WHERE id=?",
                (orc["cliente_id"],),
            ).fetchone()
        if cli:
            if not dados["uf_destino"]:
                dados["uf_destino"] = (cli["uf"] or "").strip().upper() or None
            if not dados["tipo_cliente"]:
                dados["tipo_cliente"] = "PJ" if cli["tipo_pessoa"] == "j" else "PF"
            if not dados["contribuinte"]:
                dados["contribuinte"] = cli["contribuinte"] or None

    erros: list[dict] = []
    gravados = 0
    with system_conn() as conn:
        for it in (orc.get("itens") or []):
            qtd = float(it.get("quantidade") or 1)
            preco = float(it.get("preco_unitario") or 0)
            desc_pct = float(it.get("desconto_percentual") or 0)
            desc_r = round(preco * qtd * desc_pct / 100, 2)
            ctx = {
                **dados,
                "variante_id": it.get("produto_id"),
                "quantidade": qtd,
                "valor_unitario": preco,
                "desconto": desc_r,
            }
            res = fiscal_motor.simular(ctx)
            res["data"] = dados["data"]

            memoria = res.get("memoria") or {}
            mem_prod = res.get("memoria_produto") or {}
            valores = {k: res.get(k) for k in _COLS}
            conn.execute(
                f"INSERT INTO orcamento_itens_fiscal"
                f" (orcamento_id, item_id, produto_id, resultado_json, status_validacao,"
                f"  regra_id, regra_nome, regra_versao, regra_fonte, regra_origem,"
                f"  regra_produto_id, regra_produto_nome, regra_produto_versao, {', '.join(_COLS)})"
                f" VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,{', '.join('?' for _ in _COLS)})",
                (
                    orcamento_id, it.get("id"), it.get("produto_id"),
                    json.dumps(res, ensure_ascii=False),
                    res.get("status_validacao"),
                    memoria.get("regra_id"), memoria.get("regra_nome"),
                    memoria.get("versao"), memoria.get("fonte"), memoria.get("origem"),
                    mem_prod.get("regra_id"), mem_prod.get("regra_nome"),
                    mem_prod.get("versao"),
                    *(valores[c] for c in _COLS),
                ),
            )
            gravados += 1
            bloqueia = any(
                p.get("tipo") == "ERROR" and p.get("campo") in CAMPOS_BLOQUEANTES
                for p in res.get("problemas", [])
            )
            if bloqueia:
                erros.append({
                    "item": it.get("nome"),
                    "problemas": [p for p in res.get("problemas", [])
                                  if p.get("tipo") == "ERROR" and p.get("campo") in CAMPOS_BLOQUEANTES],
                })
    return {"itens": gravados, "erros": erros, "pode_finalizar": not erros}
