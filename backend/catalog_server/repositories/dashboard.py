"""Indicadores do painel (Dashboard) — consolidados do ERP.

Agrega vendas, contas a receber/pagar, estoque e top produtos usando as
estruturas já existentes (orcamentos, contas_receber/pagar, estoque_saldo,
variantes, produtos_cadastro).
"""
from __future__ import annotations

from datetime import date, timedelta

from catalog_server.db import system_conn


def _hoje() -> str:
    return date.today().isoformat()


def resumo() -> dict:
    hoje = _hoje()
    mes_inicio = hoje[:8] + "01"
    dias30 = (date.today() - timedelta(days=30)).isoformat()

    with system_conn() as conn:
        vendas_hoje = conn.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(total),0) t FROM orcamentos"
            " WHERE status IN ('finalizado','fechado','recebido') AND date(criado_em)=?",
            (hoje,),
        ).fetchone()
        vendas_mes = conn.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(total),0) t FROM orcamentos"
            " WHERE status IN ('finalizado','fechado','recebido') AND date(criado_em)>=?",
            (mes_inicio,),
        ).fetchone()
        receber_a_vencer = conn.execute(
            "SELECT COALESCE(SUM(saldo),0) t FROM contas_receber"
            " WHERE status='aberto' AND data_vencimento>=?",
            (hoje,),
        ).fetchone()
        receber_vencidas = conn.execute(
            "SELECT COALESCE(SUM(saldo),0) t FROM contas_receber"
            " WHERE status='aberto' AND data_vencimento<?",
            (hoje,),
        ).fetchone()
        pagar_a_vencer = conn.execute(
            "SELECT COALESCE(SUM(saldo),0) t FROM contas_pagar"
            " WHERE status='aberto' AND data_vencimento>=?",
            (hoje,),
        ).fetchone()
        estoque_baixo = conn.execute(
            "SELECT COUNT(*) n FROM estoque_saldo"
            " WHERE estoque_minimo > 0 AND quantidade <= estoque_minimo"
        ).fetchone()
        valor_estoque = conn.execute(
            "SELECT COALESCE(SUM(s.quantidade * COALESCE(p.custo_unitario,0)),0) t"
            " FROM estoque_saldo s JOIN produtos_cadastro p ON p.id=s.produto_id"
        ).fetchone()

    return {
        "hoje": hoje,
        "vendas_hoje": {"n": vendas_hoje["n"], "total": round(float(vendas_hoje["t"]), 2)},
        "vendas_mes": {"n": vendas_mes["n"], "total": round(float(vendas_mes["t"]), 2)},
        "receber_a_vencer": round(float(receber_a_vencer["t"]), 2),
        "receber_vencidas": round(float(receber_vencidas["t"]), 2),
        "pagar_a_vencer": round(float(pagar_a_vencer["t"]), 2),
        "estoque_baixo": estoque_baixo["n"],
        "valor_estoque": round(float(valor_estoque["t"]), 2),
        "periodo_top": dias30,
    }


def estoque_baixo_lista(limit: int = 10) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT s.produto_id, p.nome, p.sku, s.quantidade, s.estoque_minimo, s.deposito_id, d.nome AS deposito"
            " FROM estoque_saldo s"
            " JOIN produtos_cadastro p ON p.id=s.produto_id"
            " LEFT JOIN depositos d ON d.id=s.deposito_id"
            " WHERE s.estoque_minimo > 0 AND s.quantidade <= s.estoque_minimo"
            " ORDER BY (s.quantidade - s.estoque_minimo) ASC LIMIT ?",
            (limit,),
        ).fetchall()]


def top_vendas(limit: int = 5) -> list[dict]:
    dias30 = (date.today() - timedelta(days=30)).isoformat()
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT p.nome, p.sku, SUM(oi.quantidade) AS qtd,"
            " SUM(oi.preco_unitario * oi.quantidade) AS receita"
            " FROM orcamento_itens oi"
            " JOIN orcamentos o ON o.id=oi.orcamento_id"
            "  AND o.status IN ('finalizado','fechado','recebido') AND date(o.criado_em)>=?"
            " JOIN produtos_cadastro p ON p.id=oi.produto_id"
            " GROUP BY oi.produto_id, p.nome, p.sku ORDER BY receita DESC LIMIT ?",
            (dias30, limit),
        ).fetchall()]
