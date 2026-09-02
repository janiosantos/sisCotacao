"""Relatórios e indicadores (BI-001..007): camada de consultas analíticas
(dashboard executivo, vendas, compras, estoque, financeiro/DRE e central).
Agregações pesadas separadas das operacionais; snapshot de período.
"""

from __future__ import annotations

from datetime import date

from catalog_server.db import system_conn


def _periodo(data_inicio: str | None, data_fim: str | None) -> tuple[str, str]:
    inicio = (data_inicio or "1900-01-01").strip()
    fim = (data_fim or date.today().isoformat()).strip()
    return inicio, fim


# ─── BI-001: consultas analíticas (sem bloquear operação) ───

# As queries abaixo agregam a partir do ledger/documentos; nada é gravado na
# transação operacional. O snapshot de período é explícito em cada chamada.


# ─── BI-002: Dashboard executivo ───────────────────────────

def dashboard_executivo(data_inicio: str | None = None, data_fim: str | None = None) -> dict:
    inicio, fim = _periodo(data_inicio, data_fim)
    with system_conn() as conn:
        vendas = conn.execute(
            """SELECT
                 COUNT(DISTINCT o.id) AS pedidos,
                 COALESCE(SUM(o.total),0) AS receita_bruta,
                 COALESCE(SUM(o.desconto),0) AS desconto,
                 COALESCE(SUM(COALESCE(NULLIF(o.total_liquido, 0), o.total - o.desconto)),0) AS receita_liquida
               FROM orcamentos o
               WHERE o.status IN ('finalizado','recebido')
                 AND SUBSTR(o.criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        custo = conn.execute(
            """SELECT COALESCE(SUM(custo_unitario * quantidade),0) AS cmv
               FROM estoque_movimento
               WHERE tipo='saida' AND origem_tipo='venda'
                 AND SUBSTR(criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        caixa = conn.execute(
            "SELECT COALESCE((SELECT saldo_posterior FROM caixa_movimento ORDER BY id DESC LIMIT 1),0) AS saldo"
        ).fetchone()
        inadimplencia = conn.execute(
            """SELECT COALESCE(SUM(saldo),0) AS valor FROM contas_receber
               WHERE status='aberto' AND data_vencimento::date < CURRENT_DATE"""
        ).fetchone()
        estoque_val = conn.execute(
            "SELECT COALESCE(SUM(quantidade * custo_medio),0) AS valor FROM estoque_saldo"
        ).fetchone()
        compras_abertas = conn.execute(
            """SELECT COALESCE(SUM(pi.quantidade * pi.preco_unitario),0) AS valor
               FROM pedido_itens pi JOIN pedidos_compra pc ON pc.id=pi.pedido_id
               WHERE pc.status NOT IN ('recebido','cancelado')"""
        ).fetchone()

        receita_liquida = float(vendas["receita_liquida"] or 0)
        cmv = float(custo["cmv"] or 0)
        ticket = round(receita_liquida / int(vendas["pedidos"] or 0), 2) if int(vendas["pedidos"] or 0) else 0.0
        margem = round((receita_liquida - cmv) / receita_liquida * 100, 1) if receita_liquida > 0 else 0.0
    return {
        "periodo": {"inicio": inicio, "fim": fim},
        "kpis": {
            "pedidos": int(vendas["pedidos"] or 0),
            "receita_bruta": round(float(vendas["receita_bruta"] or 0), 2),
            "desconto": round(float(vendas["desconto"] or 0), 2),
            "receita_liquida": receita_liquida,
            "cmv": round(cmv, 2),
            "margem_pct": margem,
            "ticket_medio": ticket,
            "caixa": round(float(caixa["saldo"] or 0), 2),
            "inadimplencia": round(float(inadimplencia["valor"] or 0), 2),
            "estoque_valorizado": round(float(estoque_val["valor"] or 0), 2),
            "compras_abertas": round(float(compras_abertas["valor"] or 0), 2),
        },
    }


# ─── BI-003: Vendas (agrupáveis, cancelados separados) ─────

_AGRUPAMENTOS = {"produto": "oi.produto_id", "marca": "oi.marca", "grupo": "p.categoria_id",
                 "vendedor": "o.usuario_id", "cliente": "o.cliente_id", "deposito": "o.deposito_id",
                 "canal": "o.modelo_documento", "forma": "o.condicao_pagamento_id"}


def vendas(data_inicio: str | None = None, data_fim: str | None = None, agrupamento: str = "produto",
           cancelados_separados: bool = True) -> dict:
    inicio, fim = _periodo(data_inicio, data_fim)
    ag = _AGRUPAMENTOS.get((agrupamento or "produto").strip().lower(), "oi.produto_id")
    with system_conn() as conn:
        rows = conn.execute(
            f"""SELECT {ag} AS chave,
                  COALESCE(SUM(oi.quantidade * oi.preco_unitario * (1 - oi.desconto_percentual/100.0)),0) AS receita_liquida,
                  COALESCE(SUM(oi.quantidade * oi.preco_unitario),0) AS receita_bruta,
                  COUNT(DISTINCT o.id) AS pedidos
               FROM orcamento_itens oi JOIN orcamentos o ON o.id=oi.orcamento_id
               LEFT JOIN produtos_cadastro p ON p.id=oi.produto_id
               WHERE o.status IN ('finalizado','recebido')
                 AND SUBSTR(o.criado_em,1,10) BETWEEN ? AND ?
               GROUP BY {ag} ORDER BY receita_liquida DESC LIMIT 200""",
            (inicio, fim),
        ).fetchall()
        cancelados = conn.execute(
            """SELECT COALESCE(SUM(oi.quantidade * oi.preco_unitario),0) AS valor, COUNT(DISTINCT o.id) AS pedidos
               FROM orcamento_itens oi JOIN orcamentos o ON o.id=oi.orcamento_id
               WHERE o.status IN ('cancelado','devolvido')
                 AND SUBSTR(o.criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        custo = conn.execute(
            """SELECT COALESCE(SUM(custo_unitario * quantidade),0) AS cmv
               FROM estoque_movimento WHERE tipo='saida' AND origem_tipo='venda'
                 AND SUBSTR(criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
    itens = [{"chave": r["chave"], "receita_bruta": float(r["receita_bruta"] or 0),
              "receita_liquida": float(r["receita_liquida"] or 0), "pedidos": int(r["pedidos"] or 0)} for r in rows]
    return {"agrupamento": agrupamento, "itens": itens,
            "cmv": round(float(custo["cmv"] or 0), 2),
            "cancelados": {"valor": round(float(cancelados["valor"] or 0), 2), "pedidos": int(cancelados["pedidos"] or 0)},
            "cancelados_separados": cancelados_separados}


# ─── BI-004: Compras ───────────────────────────────────────

def compras(data_inicio: str | None = None, data_fim: str | None = None) -> dict:
    inicio, fim = _periodo(data_inicio, data_fim)
    with system_conn() as conn:
        pedidos = conn.execute(
            """SELECT COUNT(*) AS total,
                 COUNT(*) FILTER (WHERE status IN ('recebido','parcialmente_recebido')) AS recebidos,
                 COUNT(*) FILTER (WHERE status='cancelado') AS cancelados,
                 COALESCE(SUM(CASE WHEN status='recebido' THEN (data_recebida::date - data_pedido::date) END) /
                    NULLIF(COUNT(*) FILTER (WHERE status='recebido' AND data_recebida IS NOT NULL),0),0) AS lead_time_medio
               FROM pedidos_compra WHERE COALESCE(data_pedido, criado_em::timestamptz)::date BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        valores = conn.execute(
            """SELECT COALESCE(SUM(pi.quantidade * pi.preco_unitario),0) AS comprado
               FROM pedido_itens pi JOIN pedidos_compra pc ON pc.id=pi.pedido_id
               WHERE pc.status NOT IN ('cancelado') AND COALESCE(pc.data_pedido, pc.criado_em::timestamptz)::date BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
    return {"pedidos": int(pedidos["total"] or 0), "recebidos": int(pedidos["recebidos"] or 0),
            "cancelados": int(pedidos["cancelados"] or 0),
            "lead_time_medio_dias": round(float(pedidos["lead_time_medio"] or 0), 1),
            "comprado": round(float(valores["comprado"] or 0), 2)}


# ─── BI-005: Estoque ───────────────────────────────────────

def estoque(deposito_id: int | None = None) -> dict:
    sql = (
        """SELECT p.id, p.sku, p.nome, p.classe_abc, p.classe_xyz, p.custo_unitario,
            s.deposito_id, s.quantidade, s.custo_medio,
            (s.quantidade - s.reserva - COALESCE(s.bloqueado,0) - COALESCE(s.separacao,0)) AS disponivel,
            s.quantidade * s.custo_medio AS valor
           FROM estoque_saldo s JOIN produtos_cadastro p ON p.id=s.produto_id
           WHERE s.quantidade <> 0"""
    )
    args: list = []
    if deposito_id:
        sql += " AND s.deposito_id=?"
        args.append(deposito_id)
    sql += " ORDER BY s.quantidade * s.custo_medio DESC LIMIT 500"
    with system_conn() as conn:
        itens = [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]
        totais = conn.execute(
            """SELECT COUNT(*) AS produtos,
                 COALESCE(SUM(quantidade),0) AS unidades,
                 COALESCE(SUM(quantidade * custo_medio),0) AS valor,
                 COALESCE(SUM(CASE WHEN (quantidade - reserva - COALESCE(bloqueado,0) - COALESCE(separacao,0)) <= 0 THEN 1 ELSE 0 END),0) AS ruptura
               FROM estoque_saldo WHERE quantidade <> 0"""
            + (" AND deposito_id=?" if deposito_id else ""),
            tuple(args),
        ).fetchone()
    return {"deposito_id": deposito_id, "itens": itens,
            "totais": {"produtos": int(totais["produtos"] or 0), "unidades": float(totais["unidades"] or 0),
                       "valor": round(float(totais["valor"] or 0), 2), "ruptura": int(totais["ruptura"] or 0)}}


# ─── BI-006: Financeiro / DRE ──────────────────────────────

def financeiro(data_inicio: str | None = None, data_fim: str | None = None) -> dict:
    inicio, fim = _periodo(data_inicio, data_fim)
    with system_conn() as conn:
        fluxo = conn.execute(
            """SELECT COALESCE(SUM(valor) FILTER (WHERE tipo IN ('entrada','abertura','suprimento')),0) AS entradas,
                 COALESCE(SUM(valor) FILTER (WHERE tipo IN ('saida','sangria')),0) AS saidas
               FROM caixa_movimento WHERE SUBSTR(criado_em,1,10) BETWEEN ? AND ?""",
            (inicio, fim),
        ).fetchone()
        aging = conn.execute(
            """SELECT COALESCE(SUM(saldo) FILTER (WHERE data_vencimento::date >= CURRENT_DATE),0) AS a_vencer,
                 COALESCE(SUM(saldo) FILTER (WHERE data_vencimento::date < CURRENT_DATE),0) AS vencido,
                 COALESCE(SUM(saldo),0) AS total
               FROM contas_receber WHERE status IN ('aberto','parcial')"""
        ).fetchone()
        dre = conn.execute(
            """SELECT
                 (SELECT COALESCE(SUM(COALESCE(NULLIF(total_liquido, 0), total - desconto)),0) FROM orcamentos WHERE status IN ('finalizado','recebido') AND SUBSTR(criado_em,1,10) BETWEEN ? AND ?) AS receita,
                 (SELECT COALESCE(SUM(custo_unitario * quantidade),0) FROM estoque_movimento WHERE tipo='saida' AND origem_tipo='venda' AND SUBSTR(criado_em,1,10) BETWEEN ? AND ?) AS cmv""",
            (inicio, fim, inicio, fim),
        ).fetchone()
    receita = float(dre["receita"] or 0)
    cmv = float(dre["cmv"] or 0)
    return {
        "fluxo_caixa": {"entradas": round(float(fluxo["entradas"] or 0), 2), "saidas": round(float(fluxo["saidas"] or 0), 2)},
        "aging": {"a_vencer": round(float(aging["a_vencer"] or 0), 2), "vencido": round(float(aging["vencido"] or 0), 2),
                  "total": round(float(aging["total"] or 0), 2)},
        "dre": {"receita_liquida": round(receita, 2), "cmv": round(cmv, 2),
                "lucro_bruto": round(receita - cmv, 2)},
    }


# ─── BI-007: Central de relatórios ─────────────────────────

CATALOGO = [
    {"key": "dashboard", "nome": "Dashboard executivo", "grupo": "executivo", "permissao": "relatorios.visualizar"},
    {"key": "vendas", "nome": "Vendas", "grupo": "vendas", "permissao": "relatorios.visualizar", "filtros": ["periodo", "agrupamento"]},
    {"key": "compras", "nome": "Compras", "grupo": "compras", "permissao": "relatorios.visualizar", "filtros": ["periodo"]},
    {"key": "estoque", "nome": "Estoque", "grupo": "estoque", "permissao": "relatorios.visualizar", "filtros": ["deposito"]},
    {"key": "financeiro", "nome": "Financeiro / DRE", "grupo": "financeiro", "permissao": "relatorios.financeiro", "filtros": ["periodo"]},
]


def central() -> dict:
    return {"relatorios": CATALOGO}
