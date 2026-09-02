"""Relatorio financeiro gerencial com aging e DRE conciliavel.

Este modulo nao pretende substituir a contabilidade legal. Ele explicita o
regime usado (caixa para fluxo e competencia para resultado) e devolve os
titulos que formam os totais para auditoria operacional.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Mapping

from catalog_server.db import system_conn


class RelatorioFinanceiroError(ValueError):
    pass


def _periodo(filters: Mapping[str, object]) -> tuple[str, str]:
    hoje = date.today()
    inicio = str(filters.get("data_inicio") or date(hoje.year, 1, 1)).strip()
    fim = str(filters.get("data_fim") or hoje).strip()
    try:
        inicio_dt, fim_dt = date.fromisoformat(inicio), date.fromisoformat(fim)
    except ValueError as exc:
        raise RelatorioFinanceiroError("Periodo deve usar o formato AAAA-MM-DD") from exc
    if inicio_dt > fim_dt:
        raise RelatorioFinanceiroError("data_inicio nao pode ser maior que data_fim")
    if fim_dt - inicio_dt > timedelta(days=3660):
        raise RelatorioFinanceiroError("O periodo maximo do relatorio e de 10 anos")
    return inicio, fim


def _pagination(filters: Mapping[str, object]) -> tuple[int, int]:
    try:
        limit, offset = int(filters.get("limit") or 50), int(filters.get("offset") or 0)
    except (TypeError, ValueError) as exc:
        raise RelatorioFinanceiroError("limit e offset devem ser inteiros") from exc
    if limit < 1 or limit > 200 or offset < 0 or offset > 1_000_000:
        raise RelatorioFinanceiroError("paginacao fora do limite permitido")
    return limit, offset


def _money(value) -> float:
    return round(float(value or 0), 2)


def _aging(conn, table: str, cutoff: str) -> list[dict]:
    if table not in {"contas_receber", "contas_pagar"}:
        raise RelatorioFinanceiroError("tabela financeira invalida")
    rows = conn.execute(
        f"""SELECT CASE
                    WHEN data_vencimento::date >= ?::date THEN 'a_vencer'
                    WHEN (?::date - data_vencimento::date) BETWEEN 0 AND 30 THEN 'vencido_0_30'
                    WHEN (?::date - data_vencimento::date) BETWEEN 31 AND 60 THEN 'vencido_31_60'
                    WHEN (?::date - data_vencimento::date) BETWEEN 61 AND 90 THEN 'vencido_61_90'
                    ELSE 'vencido_91_mais' END AS faixa,
                 COUNT(*) AS quantidade, COALESCE(SUM(saldo),0) AS saldo
                 FROM {table} WHERE status IN ('aberto','parcial')
                 GROUP BY 1""",
        (cutoff, cutoff, cutoff, cutoff),
    ).fetchall()
    known = {"a_vencer": 0, "vencido_0_30": 0, "vencido_31_60": 0, "vencido_61_90": 0, "vencido_91_mais": 0}
    values = {key: {"quantidade": 0, "saldo": 0.0} for key in known}
    for row in rows:
        key = row["faixa"]
        if key in values:
            values[key] = {"quantidade": int(row["quantidade"] or 0), "saldo": _money(row["saldo"])}
    return [{"faixa": key, **values[key]} for key in known]


def gerar(filters: Mapping[str, object] | None = None) -> dict:
    filters = filters or {}
    inicio, fim = _periodo(filters)
    limit, offset = _pagination(filters)
    cutoff = str(filters.get("data_corte") or fim).strip()
    try:
        date.fromisoformat(cutoff)
    except ValueError as exc:
        raise RelatorioFinanceiroError("data_corte deve usar o formato AAAA-MM-DD") from exc
    tipo = str(filters.get("tipo") or "todos").strip().lower()
    if tipo not in {"todos", "receber", "pagar"}:
        raise RelatorioFinanceiroError("tipo deve ser todos, receber ou pagar")
    termo = str(filters.get("q") or "").strip()
    like = f"%{termo}%"
    with system_conn() as conn:
        aging_receber = _aging(conn, "contas_receber", cutoff)
        aging_pagar = _aging(conn, "contas_pagar", cutoff)
        linhas = """
            SELECT 'receber' AS tipo, cr.id, cr.documento, cr.descricao,
                   COALESCE(cr.cliente,'') AS pessoa, cr.valor, cr.saldo,
                   cr.data_emissao, cr.data_vencimento, cr.status
            FROM contas_receber cr
            WHERE cr.status IN ('aberto','parcial')
              AND cr.data_vencimento::date BETWEEN ?::date AND ?::date
            UNION ALL
            SELECT 'pagar', cp.id, cp.documento, cp.descricao,
                   COALESCE(cp.fornecedor,'') AS pessoa, cp.valor, cp.saldo,
                   cp.data_emissao, cp.data_vencimento, cp.status
            FROM contas_pagar cp
            WHERE cp.status IN ('aberto','parcial')
              AND cp.data_vencimento::date BETWEEN ?::date AND ?::date
        """
        parts = []
        args: list[object] = [inicio, fim, inicio, fim]
        if tipo != "todos":
            parts.append("tipo=?")
            args.append(tipo)
        if termo:
            parts.append("(LOWER(COALESCE(pessoa,'')) LIKE LOWER(?) OR LOWER(COALESCE(descricao,'')) LIKE LOWER(?) OR COALESCE(documento,'') LIKE ?)")
            args.extend([like, like, like])
        condition = f" WHERE {' AND '.join(parts)}" if parts else ""
        total = int(conn.execute(f"SELECT COUNT(*) AS total FROM ({linhas}) titulos{condition}", tuple(args)).fetchone()["total"] or 0)
        rows = conn.execute(
            f"SELECT * FROM ({linhas}) titulos{condition} ORDER BY data_vencimento::date, id LIMIT ? OFFSET ?",
            tuple([*args, limit, offset]),
        ).fetchall()
        fluxo = conn.execute(
            """SELECT COALESCE(SUM(valor) FILTER (WHERE tipo IN ('entrada','abertura','suprimento')),0) AS entradas,
                      COALESCE(SUM(valor) FILTER (WHERE tipo IN ('saida','sangria')),0) AS saidas
               FROM caixa_movimento WHERE SUBSTR(criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        vendas = conn.execute(
            """SELECT COALESCE(SUM(total - desconto),0) AS receita_bruta,
                      COALESCE(SUM(COALESCE(NULLIF(total_liquido,0),total-desconto)),0) AS receita_liquida,
                      COALESCE(SUM(desconto),0) AS descontos
               FROM orcamentos WHERE status IN ('finalizado','recebido') AND SUBSTR(criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        cmv = conn.execute(
            """SELECT COALESCE(SUM(custo_unitario * quantidade),0) AS cmv
               FROM estoque_movimento WHERE tipo='saida' AND origem_tipo='venda' AND SUBSTR(criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        despesas = conn.execute(
            """SELECT COALESCE(pc.nome,'Sem classificacao') AS categoria, COALESCE(SUM(cp.valor),0) AS valor
               FROM contas_pagar cp LEFT JOIN plano_de_contas pc ON pc.id=cp.plano_conta_id
               WHERE cp.status='pago' AND COALESCE(cp.data_pagamento,cp.data_emissao)::date BETWEEN ?::date AND ?::date
               GROUP BY pc.nome ORDER BY valor DESC""",
            (inicio, fim),
        ).fetchall()
    receita = _money(vendas["receita_liquida"])
    custo = _money(cmv["cmv"])
    return {
        "report_key": "financeiro.analitico", "kind": "analitico", "calculation_version": "1.0",
        "regime": {"resultado": "competencia operacional", "fluxo": "caixa", "data_corte_aging": cutoff},
        "periodo": {"inicio": inicio, "fim": fim}, "filtros": dict(filters),
        "aging": {"receber": aging_receber, "pagar": aging_pagar},
        "fluxo_caixa": {"entradas": _money(fluxo["entradas"]), "saidas": _money(fluxo["saidas"]), "liquido": _money(fluxo["entradas"]) - _money(fluxo["saidas"])},
        "dre": {"receita_bruta": _money(vendas["receita_bruta"]), "descontos": _money(vendas["descontos"]), "receita_liquida": receita, "cmv": custo, "lucro_bruto": _money(receita - custo), "despesas_pagamento": _money(sum(float(row["valor"] or 0) for row in despesas)), "despesas_por_categoria": [{"categoria": row["categoria"], "valor": _money(row["valor"])} for row in despesas]},
        "itens": [{**dict(row), "valor": _money(row["valor"]), "saldo": _money(row["saldo"])} for row in rows],
        "paginacao": {"total": total, "limit": limit, "offset": offset, "proximo_offset": offset + limit if offset + limit < total else None},
    }
