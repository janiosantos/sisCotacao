from __future__ import annotations

from catalog_server.db import system_conn


class RelatorioRepository:

    def vendas_por_periodo(self, data_inicio: str, data_fim: str) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT date(criado_em) AS dia, COUNT(*) AS n_pedidos,"
                " COALESCE(SUM(total),0) AS total_vendas"
                " FROM orcamentos WHERE status IN ('fechado','faturado')"
                " AND date(criado_em) BETWEEN ? AND ?"
                " GROUP BY date(criado_em) ORDER BY dia",
                (data_inicio, data_fim),
            ).fetchall()]

    def aging_receber(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT 'a_vencer' AS faixa, COUNT(*) AS qtd, COALESCE(SUM(saldo),0) AS total
                FROM contas_receber WHERE status='aberto' AND data_vencimento >= date('now')
                UNION ALL
                SELECT 'vencidos_30' AS faixa, COUNT(*), COALESCE(SUM(saldo),0)
                FROM contas_receber WHERE status='aberto' AND data_vencimento BETWEEN date('now','-30 days') AND date('now')
                UNION ALL
                SELECT 'vencidos_60', COUNT(*), COALESCE(SUM(saldo),0)
                FROM contas_receber WHERE status='aberto' AND data_vencimento BETWEEN date('now','-60 days') AND date('now','-31 days')
                UNION ALL
                SELECT 'vencidos_90_mais', COUNT(*), COALESCE(SUM(saldo),0)
                FROM contas_receber WHERE status='aberto' AND data_vencimento < date('now','-60 days')
            """).fetchall()]

    def aging_pagar(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT 'a_vencer' AS faixa, COUNT(*) AS qtd, COALESCE(SUM(saldo),0) AS total
                FROM contas_pagar WHERE status='aberto' AND data_vencimento >= date('now')
                UNION ALL
                SELECT 'vencidos_30', COUNT(*), COALESCE(SUM(saldo),0)
                FROM contas_pagar WHERE status='aberto' AND data_vencimento BETWEEN date('now','-30 days') AND date('now')
                UNION ALL
                SELECT 'vencidos_60', COUNT(*), COALESCE(SUM(saldo),0)
                FROM contas_pagar WHERE status='aberto' AND data_vencimento BETWEEN date('now','-60 days') AND date('now','-31 days')
                UNION ALL
                SELECT 'vencidos_90_mais', COUNT(*), COALESCE(SUM(saldo),0)
                FROM contas_pagar WHERE status='aberto' AND data_vencimento < date('now','-60 days')
            """).fetchall()]

    def dre_resumido(self, data_inicio: str, data_fim: str) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute("""
                SELECT 'receitas' AS tipo, COALESCE(SUM(total),0) AS valor
                FROM orcamentos WHERE status IN ('fechado','faturado')
                AND date(criado_em) BETWEEN ? AND ?
                UNION ALL
                SELECT 'despesas', COALESCE(SUM(valor),0)
                FROM contas_pagar WHERE status='pago'
                AND date(data_pagamento) BETWEEN ? AND ?
            """, (data_inicio, data_fim, data_inicio, data_fim)).fetchall()]


relatorio_repo = RelatorioRepository()
