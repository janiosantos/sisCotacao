"""ABC histórica (COM-001): cálculo reproduzível por período, depósito e
critério (consumo, receita, margem, quantidade, frequência), versionado.
Exclui cancelamentos/devoluções. ABC estimada (bootstrap) permanece como fallback.
"""

from __future__ import annotations

import json

from catalog_server.db import system_conn

CRITERIOS = ("consumo", "receita", "margem", "quantidade", "frequencia")
CLASSE_A_LIMITE = 0.70
CLASSE_B_LIMITE = 0.90


def _metricas(data_inicio: str, data_fim: str) -> list[dict]:
    """Métricas por produto a partir do ledger e das vendas finalizadas."""
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            """
            WITH vendas AS (
                SELECT oi.produto_id,
                       SUM(oi.quantidade) AS quantidade,
                       SUM(oi.quantidade * oi.preco_unitario) AS receita,
                       COUNT(DISTINCT SUBSTR(o.criado_em,1,10)) AS frequencia
                FROM orcamento_itens oi
                JOIN orcamentos o ON o.id = oi.orcamento_id
                WHERE o.status = 'finalizado'
                  AND SUBSTR(o.criado_em,1,10) BETWEEN ? AND ?
                GROUP BY oi.produto_id
            ),
            custos AS (
                SELECT produto_id, SUM(COALESCE(custo_unitario,0) * quantidade) AS custo_total
                FROM estoque_movimento
                WHERE tipo='saida' AND origem_tipo='venda'
                  AND SUBSTR(criado_em,1,10) BETWEEN ? AND ?
                GROUP BY produto_id
            )
            SELECT v.produto_id, v.quantidade, v.receita, v.frequencia,
                   v.receita - COALESCE(c.custo_total,0) AS margem
            FROM vendas v LEFT JOIN custos c ON c.produto_id = v.produto_id
            """,
            (data_inicio, data_fim, data_inicio, data_fim),
        ).fetchall()]


def _valor(m: dict, criterio: str) -> float:
    return float(m.get(criterio) or 0.0)


def calcular(
    criterio: str,
    data_inicio: str,
    data_fim: str,
    deposito_id: int | None = None,
    usuario_id: int | None = None,
) -> dict:
    criterio = (criterio or "").strip().lower()
    if criterio not in CRITERIOS:
        raise ValueError(f"critério inválido (use: {', '.join(CRITERIOS)})")
    if not data_inicio or not data_fim:
        raise ValueError("data_inicio e data_fim são obrigatórios")
    if data_inicio > data_fim:
        raise ValueError("data_inicio deve ser <= data_fim")

    metricas = _metricas(data_inicio, data_fim)
    linhas = [
        {"produto_id": m["produto_id"], "valor": round(_valor(m, criterio), 4),
         "metricas": m}
        for m in metricas
    ]
    # Produtos com valor 0 no critério mas com venda ficam no fim; itens sem
    # venda (zero em tudo) são separados.
    linhas.sort(key=lambda r: r["valor"], reverse=True)
    total = sum(r["valor"] for r in linhas)
    acumulado = 0.0
    itens = []
    sem_venda = 0
    for ordem, r in enumerate(linhas, start=1):
        acumulado += r["valor"]
        pct = (acumulado / total) if total > 0 else 0.0
        if total <= 0 or r["valor"] <= 0:
            classe = "C"
            if _valor(r["metricas"], "quantidade") == 0 and _valor(r["metricas"], "receita") == 0:
                sem_venda += 1
        elif pct <= CLASSE_A_LIMITE:
            classe = "A"
        elif pct <= CLASSE_B_LIMITE:
            classe = "B"
        else:
            classe = "C"
        itens.append({
            "produto_id": r["produto_id"],
            "valor": r["valor"],
            "acumulado": round(acumulado, 4),
            "pct_acumulado": round(pct, 4),
            "classe": classe,
            "ordem": ordem,
        })

    with system_conn() as conn:
        calc_id = conn.execute(
            "INSERT INTO abc_calculo (criterio, data_inicio, data_fim, deposito_id,"
            " parametros, origem, total, acumulado, criado_por)"
            " VALUES (?,?,?,?,?, 'historico', ?, ?, ?) RETURNING id",
            (criterio, data_inicio, data_fim, deposito_id,
             json.dumps({"classe_a_limite": CLASSE_A_LIMITE, "classe_b_limite": CLASSE_B_LIMITE}),
             round(total, 4),
             json.dumps({"A": CLASSE_A_LIMITE, "B": CLASSE_B_LIMITE, "C": 1.0}),
             usuario_id),
        ).fetchone()["id"]
        for it in itens:
            conn.execute(
                "INSERT INTO abc_calculo_item (calculo_id, produto_id, valor, acumulado,"
                " pct_acumulado, classe, ordem) VALUES (?,?,?,?,?,?,?)",
                (calc_id, it["produto_id"], it["valor"], it["acumulado"],
                 it["pct_acumulado"], it["classe"], it["ordem"]),
            )

    return {
        "id": calc_id,
        "criterio": criterio,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total": round(total, 4),
        "itens": itens,
        "total_itens": len(itens),
        "sem_venda": sem_venda,
        "resumo": _resumo_por_classe(itens, total),
    }


def _resumo_por_classe(itens: list[dict], total: float) -> dict:
    resumo: dict[str, dict] = {c: {"produtos": 0, "valor": 0.0} for c in ("A", "B", "C")}
    for it in itens:
        c = it["classe"]
        r = resumo[c]
        r["produtos"] += 1
        r["valor"] += float(it["valor"])
    for c, r in resumo.items():
        r["pct"] = round(r["valor"] / float(total) * 100, 1) if total > 0 else 0.0
    return resumo


def aplicar(calculo_id: int) -> dict:
    """Aplica a classe/ordem da versão escolhida nos produtos (somente os com
    histórico). Produtos sem venda mantêm a ABC bootstrap identificada."""
    with system_conn() as conn:
        calc = conn.execute(
            "SELECT criterio, data_inicio, data_fim FROM abc_calculo WHERE id=?",
            (calculo_id,),
        ).fetchone()
        if not calc:
            raise LookupError("Cálculo ABC não encontrado")
        itens = conn.execute(
            "SELECT produto_id, classe, ordem FROM abc_calculo_item WHERE calculo_id=?",
            (calculo_id,),
        ).fetchall()
        for it in itens:
            conn.execute(
                "UPDATE produtos_cadastro SET classe_abc=?, ordem_abc=?, abc_origem='historico'"
                " WHERE id=?",
                (it["classe"], it["ordem"], it["produto_id"]),
            )
    return {"aplicados": len(itens),
            "criterio": calc["criterio"],
            "periodo": f"{calc['data_inicio']} a {calc['data_fim']}"}


def listar(deposito_id: int | None = None) -> list[dict]:
    sql = (
        "SELECT c.id, c.criterio, c.data_inicio, c.data_fim, c.deposito_id,"
        " c.origem, c.total, c.criado_por, c.criado_em,"
        " (SELECT COUNT(*) FROM abc_calculo_item i WHERE i.calculo_id=c.id) AS itens"
        " FROM abc_calculo c"
    )
    args: list = []
    if deposito_id:
        sql += " WHERE c.deposito_id=?"
        args.append(deposito_id)
    sql += " ORDER BY c.id DESC"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def detalhe(calculo_id: int) -> dict | None:
    with system_conn() as conn:
        calc = conn.execute(
            "SELECT * FROM abc_calculo c"
            " WHERE c.id=?", (calculo_id,),
        ).fetchone()
        if not calc:
            return None
        itens = [dict(r) for r in conn.execute(
            "SELECT i.*, p.sku, p.nome AS produto_nome FROM abc_calculo_item i"
            " JOIN produtos_cadastro p ON p.id=i.produto_id"
            " WHERE i.calculo_id=? ORDER BY i.ordem",
            (calculo_id,),
        ).fetchall()]
        out = dict(calc)
        out["itens"] = itens
        out["resumo"] = _resumo_por_classe(itens, float(out.get("total") or 0))
        return out