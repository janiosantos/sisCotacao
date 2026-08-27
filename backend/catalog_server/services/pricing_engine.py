"""Motor de Precificação.

Consome o Motor de Custo (`custo_engine.calcular_custo`) — que por sua vez
consome o Motor Fiscal — e aplica os componentes de venda para calcular o preço
mínimo e o preço sugerido de uma variante.

Regras (documentadas):
- Custo líquido vem do módulo de Custo (tributos/créditos já tratados no Fiscal).
- Preço por MARGEM (sobre a venda), padrão do varejo:
      preco = custo_liquido / (1 − (despesas + comissão + taxas + margem) / 100)
- Preço por MARKUP (sobre o custo), quando informado no lugar da margem:
      preco = custo_liquido × (1 + markup / 100)
- Preço mínimo = cobre custo + despesas variáveis (margem zero):
      preco_minimo = custo_liquido / (1 − (despesas + comissão + taxas) / 100)

Margem e markup são mutuamente exclusivos (margem tem prioridade). O canal pode
selecionar a tabela de preço correspondente (varejo/atacado/contrato/promocional)
para herdar margem_padrao/markup.

Este módulo NÃO recalcula tributos nem créditos (responsabilidade do Fiscal).
"""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import custo_engine


def _tabela_do_canal(canal: str | None, tabela_id: int | None) -> dict | None:
    with system_conn() as conn:
        if tabela_id:
            row = conn.execute(
                "SELECT * FROM tabelas_preco WHERE id=? AND ativo=1", (tabela_id,)
            ).fetchone()
        elif canal:
            row = conn.execute(
                "SELECT * FROM tabelas_preco WHERE tipo=? AND ativo=1 ORDER BY id LIMIT 1",
                (canal,),
            ).fetchone()
        else:
            return None
        return dict(row) if row else None


def calcular_preco(
    variante_id: int,
    canal: str | None = None,
    margem: float | None = None,
    markup: float | None = None,
    comissao: float = 0.0,
    despesas: float = 0.0,
    taxas: float = 0.0,
    tabela_id: int | None = None,
    fornecedor_id: int | None = None,
) -> dict:
    canal = canal if canal in ("varejo", "atacado", "contrato", "promocional") else None
    comissao = max(0.0, float(comissao or 0))
    despesas = max(0.0, float(despesas or 0))
    taxas = max(0.0, float(taxas or 0))
    despesas_total = round(comissao + despesas + taxas, 4)

    custo = custo_engine.calcular_custo(variante_id, fornecedor_id=fornecedor_id)
    tabela = _tabela_do_canal(canal, tabela_id)
    base = {
        "variante_id": variante_id,
        "canal": canal,
        "tabela_id": tabela["id"] if tabela else (tabela_id or None),
        "tabela_nome": (tabela.get("nome") if tabela else None),
        "custo_base": custo.get("custo_base"),
        "custo_liquido": custo.get("custo_liquido"),
        "regime": custo.get("regime"),
        "despesas_pct": {"comissao": comissao, "despesas": despesas, "taxas": taxas, "total": despesas_total},
        "preco_minimo": None,
        "preco_sugerido": None,
        "margem_efetiva_pct": None,
        "markup_efetivo_pct": None,
        "observacao": None,
    }
    if custo.get("custo_liquido") is None:
        base["observacao"] = "Sem custo de aquisição definido."
        return base

    custo_liq = float(custo["custo_liquido"])
    margem_final = float(margem) if margem is not None else float((tabela or {}).get("margem_padrao") or 0)
    markup_final = float(markup) if markup is not None else float((tabela or {}).get("markup") or 0)

    def _preco_com_margem(m: float) -> float:
        divisor = 1 - (despesas_total + m) / 100
        return round(custo_liq / divisor, 2) if divisor > 0.01 else float("nan")

    if margem_final > 0:
        preco_sugerido = _preco_com_margem(margem_final)
        margem_efetiva = margem_final
        markup_efetivo = round((preco_sugerido / custo_liq - 1) * 100, 2) if custo_liq > 0 else None
        base["margem_efetiva_pct"] = margem_efetiva
        base["markup_efetivo_pct"] = markup_efetivo
        base["preco_sugerido"] = preco_sugerido
        base["observacao"] = "Margem sobre a venda"
    elif markup_final > 0:
        preco_sugerido = round(custo_liq * (1 + markup_final / 100), 2)
        margem_efetiva = round((preco_sugerido - custo_liq) / preco_sugerido * 100, 2) if preco_sugerido > 0 else None
        base["margem_efetiva_pct"] = margem_efetiva
        base["markup_efetivo_pct"] = markup_final
        base["preco_sugerido"] = preco_sugerido
        base["observacao"] = "Markup sobre o custo"
    else:
        preco_sugerido = custo_liq
        base["margem_efetiva_pct"] = 0.0
        base["preco_sugerido"] = preco_sugerido
        base["observacao"] = "Sem margem/markup configurados"

    preco_minimo = _preco_com_margem(0.0)
    base["preco_minimo"] = preco_minimo
    if preco_sugerido is None or preco_sugerido != preco_sugerido:  # NaN
        base["preco_sugerido"] = None
        base["observacao"] = "Despesas+margem >= 100%; ajuste os percentuais."
    return base


def preco_efetivo(variante_id: int, canal: str = "varejo") -> dict:
    """Preço efetivo de venda: tabela do canal → motor (sugerido) → preço base."""
    canal = canal if canal in ("varejo", "atacado", "contrato", "promocional") else "varejo"
    tabela = _tabela_do_canal(canal, None)
    if tabela:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT preco FROM tabela_preco_itens"
                " WHERE tabela_id=? AND produto_id=? AND ativo=1",
                (tabela["id"], variante_id),
            ).fetchone()
        if row and row["preco"]:
            return {
                "variante_id": variante_id, "canal": canal,
                "preco": float(row["preco"]), "origem": "tabela",
                "tabela_id": tabela["id"],
            }
    calc = calcular_preco(variante_id, canal=canal)
    if calc.get("preco_sugerido") is not None:
        return {
            "variante_id": variante_id, "canal": canal,
            "preco": calc["preco_sugerido"], "origem": "motor",
            "tabela_id": calc.get("tabela_id"),
            "custo_liquido": calc.get("custo_liquido"),
        }
    with system_conn() as conn:
        row = conn.execute("SELECT preco FROM produtos_cadastro WHERE id=?", (variante_id,)).fetchone()
    preco = float(row["preco"]) if row and row["preco"] else 0.0
    return {"variante_id": variante_id, "canal": canal, "preco": preco, "origem": "base"}


def previa_reajuste(
    tabela_id: int,
    margem: float | None = None,
    markup: float | None = None,
    termo: str | None = None,
    limit: int = 500,
) -> dict:
    """Prévia do reajuste em lote: calcula o preço sugerido (motor) sem gravar."""
    tabela = _tabela_do_canal(None, tabela_id) or {}
    m = margem if margem is not None else float(tabela.get("margem_padrao") or 0)
    mk = markup if markup is not None else float(tabela.get("markup") or 0)

    sql = """
        SELECT p.id, p.sku, p.preco AS preco_atual, p.nome AS produto_nome, p.marca
        FROM produtos_cadastro p
        WHERE p.ativo = 1
          AND (EXISTS (SELECT 1 FROM fornecedor_preco fp
                       WHERE fp.produto_id = p.id AND fp.ativo = 1)
               OR (p.custo_unitario IS NOT NULL AND p.custo_unitario > 0))
    """
    params: list = []
    if termo:
        like = f"%{termo}%"
        sql += " AND (p.nome LIKE ? OR p.sku LIKE ? OR p.marca LIKE ?)"
        params += [like, like, like]
    sql += " ORDER BY p.nome, p.sku LIMIT ?"
    params.append(limit)

    with system_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

    itens = []
    for r in rows:
        calc = calcular_preco(r["id"], margem=m, markup=mk, tabela_id=tabela_id)
        itens.append({
            "variante_id": r["id"],
            "sku": r["sku"],
            "produto_nome": r["produto_nome"],
            "marca": r["marca"],
            "preco_atual": r["preco_atual"] or 0,
            "custo_base": calc.get("custo_base"),
            "custo_liquido": calc.get("custo_liquido"),
            "preco_minimo": calc.get("preco_minimo"),
            "preco_sugerido": calc.get("preco_sugerido"),
            "margem_efetiva_pct": calc.get("margem_efetiva_pct"),
            "observacao": calc.get("observacao"),
        })
    return {"tabela_id": tabela_id, "margem": m, "markup": mk, "total": len(itens), "itens": itens}


def aplicar_reajuste(
    tabela_id: int,
    margem: float | None = None,
    markup: float | None = None,
    usuario_id: int | None = None,
    origem: str = "motor-precificacao",
) -> dict:
    """Aprova e grava o reajuste: atualiza tabela_preco_itens e registra o histórico."""
    prev = previa_reajuste(tabela_id, margem=margem, markup=markup)
    aplicados = 0
    sem_custo = 0
    with system_conn() as conn:
        for it in prev["itens"]:
            if it["preco_sugerido"] is None:
                sem_custo += 1
                continue
            row = conn.execute(
                "SELECT preco FROM tabela_preco_itens WHERE tabela_id=? AND produto_id=?",
                (tabela_id, it["variante_id"]),
            ).fetchone()
            preco_ant = float(row["preco"]) if row else 0.0
            conn.execute(
                "INSERT INTO tabela_preco_itens (tabela_id, produto_id, preco, margem)"
                " VALUES (?,?,?,?)"
                " ON CONFLICT(tabela_id, produto_id) DO UPDATE SET"
                " preco=excluded.preco, margem=excluded.margem",
                (tabela_id, it["variante_id"], it["preco_sugerido"], it["margem_efetiva_pct"]),
            )
            conn.execute(
                "INSERT INTO preco_historico"
                " (tabela_id, produto_id, preco_anterior, preco_novo, margem_pct, markup_pct,"
                "  tipo, origem, usuario_id)"
                " VALUES (?,?,?,?,?,?,'reajuste',?,?)",
                (
                    tabela_id,
                    it["variante_id"],
                    round(preco_ant, 2),
                    it["preco_sugerido"],
                    it["margem_efetiva_pct"],
                    prev["markup"],
                    origem,
                    usuario_id,
                ),
            )
            aplicados += 1
    return {"tabela_id": tabela_id, "aplicados": aplicados, "sem_custo": sem_custo, "total": len(prev["itens"])}
