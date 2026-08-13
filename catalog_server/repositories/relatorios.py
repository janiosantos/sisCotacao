from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import custo_engine


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

    def margem_vendas(self, data_inicio: str, data_fim: str) -> list[dict]:
        """Margem por produto vendido no período, usando o CUSTO LÍQUIDO
        (Motor Fiscal → Custo). Receita = preço de venda × quantidade."""
        with system_conn() as conn:
            rows = conn.execute("""
                SELECT v.id AS variante_id, p.nome AS produto_nome, v.sku,
                       COUNT(*) AS n_itens,
                       SUM(oi.quantidade) AS qtd_total,
                       SUM(oi.preco_unitario * oi.quantidade) AS receita
                FROM orcamento_itens oi
                JOIN orcamentos o ON o.id = oi.orcamento_id
                     AND o.status IN ('fechado','faturado')
                     AND date(o.criado_em) BETWEEN ? AND ?
                JOIN variantes v ON v.id = oi.produto_id
                JOIN produtos_cadastro p ON p.id = v.produto_id
                GROUP BY v.id
                ORDER BY receita DESC
            """, (data_inicio, data_fim)).fetchall()
            out = []
            for r in rows:
                receita = float(r["receita"] or 0)
                qtd = float(r["qtd_total"] or 0)
                calc = custo_engine.calcular_custo(r["variante_id"])
                custo_unit = calc.get("custo_liquido")
                if custo_unit is None:
                    custo_unit = calc.get("custo_base") or 0
                custo = round(qtd * float(custo_unit), 2)
                margem = round(receita - custo, 2)
                out.append({
                    **r,
                    "receita": round(receita, 2),
                    "custo_unitario": round(float(custo_unit), 2),
                    "custo": custo,
                    "margem": margem,
                    "margem_pct": round(margem / receita * 100, 2) if receita > 0 else None,
                })
            return out


relatorio_repo = RelatorioRepository()
