"""Motor de reposição (COM-004): necessidade por produto/depósito com todos os
componentes do cálculo, sem duplicar compra, respeitando unidade/lote e data
provável de ruptura.

    disponível_projetado = físico - reservado - bloqueado - separação
                           + compras_confirmadas_em_trânsito
                           - demanda_aberta
    necessidade = max(0, estoque_alvo + demanda_durante_lead_time - disponível_projetado)
"""

from __future__ import annotations

from datetime import date, timedelta

from catalog_server.db import system_conn
from catalog_server.services import estoque_parametro as parametro_svc


def _saldo(conn, deposito_id: int, produto_id: int) -> dict:
    row = conn.execute(
        "SELECT quantidade, reserva, COALESCE(bloqueado,0) AS bloqueado,"
        " COALESCE(separacao,0) AS separacao"
        " FROM estoque_saldo WHERE deposito_id=? AND produto_id=?",
        (deposito_id, produto_id),
    ).fetchone()
    if not row:
        return {"fisico": 0.0, "reservado": 0.0, "bloqueado": 0.0, "separacao": 0.0}
    return {"fisico": float(row["quantidade"] or 0), "reservado": float(row["reserva"] or 0),
            "bloqueado": float(row["bloqueado"] or 0), "separacao": float(row["separacao"] or 0)}


def _transito(conn, produto_id: int) -> float:
    """Compras confirmadas em trânsito (pedidos não recebidos/cancelados)."""
    row = conn.execute(
        """
        SELECT COALESCE(SUM(pi.quantidade),0) AS qtd
        FROM pedido_itens pi
        JOIN pedidos_compra pc ON pc.id=pi.pedido_id
        JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id
        WHERE ci.produto_id=? AND pc.status NOT IN ('recebido','cancelado')
        """,
        (produto_id,),
    ).fetchone()
    return float(row["qtd"] or 0)


def _demanda_aberta(conn, produto_id: int) -> float:
    """Demanda aberta: orçamentos firmes (em_análise/liberado) + registros abertos."""
    row = conn.execute(
        """
        SELECT COALESCE((
            SELECT SUM(oi.quantidade) FROM orcamento_itens oi
            JOIN orcamentos o ON o.id=oi.orcamento_id
            WHERE oi.produto_id=? AND o.status IN ('em_analise','liberado') AND o.virou_pedido=0
        ),0) + COALESCE((
            SELECT SUM(quantidade) FROM demanda_registro
            WHERE produto_id=? AND status='aberta'
        ),0) AS qtd
        """,
        (produto_id, produto_id),
    ).fetchone()
    return float(row["qtd"] or 0)


def _demanda_mensal(conn, produto_id: int) -> float:
    """Média mensal de vendas finalizadas nos últimos 6 meses."""
    row = conn.execute(
        """
        SELECT COALESCE(AVG(m.qtd),0) AS media FROM (
            SELECT SUM(oi.quantidade) AS qtd
            FROM orcamento_itens oi
            JOIN orcamentos o ON o.id=oi.orcamento_id
            WHERE o.status='finalizado' AND oi.produto_id=?
              AND SUBSTR(o.criado_em,1,10) >= to_char(CURRENT_DATE - interval '6 month', 'YYYY-MM-DD')
            GROUP BY SUBSTR(o.criado_em,1,7)
        ) m
        """,
        (produto_id,),
    ).fetchone()
    return float(row["media"] or 0)


def _fornecedor(conn, produto_id: int) -> dict | None:
    row = conn.execute(
        "SELECT fp.fornecedor_id, fp.ultimo_preco, fp.ultimo_prazo, f.nome AS fornecedor_nome"
        " FROM fornecedor_preferencial fp LEFT JOIN fornecedores f ON f.id=fp.fornecedor_id"
        " WHERE fp.produto_id=? ORDER BY fp.ranking, fp.id LIMIT 1",
        (produto_id,),
    ).fetchone()
    return dict(row) if row else None


def _fornecedor_lead_time(conn, fornecedor_id: int) -> int | None:
    row = conn.execute(
        "SELECT prazo_entrega_dias FROM fornecedores WHERE id=?",
        (fornecedor_id,),
    ).fetchone()
    return int(row["prazo_entrega_dias"]) if row and row["prazo_entrega_dias"] else None


def calcular(produto_id: int | None = None, deposito_id: int | None = None) -> dict:
    with system_conn() as conn:
        if produto_id:
            if not deposito_id:
                row = conn.execute(
                    "SELECT deposito_id FROM estoque_saldo WHERE produto_id=? ORDER BY id LIMIT 1",
                    (produto_id,),
                ).fetchone()
                deposito_id = int(row["deposito_id"]) if row else None
                if deposito_id is None:
                    row = conn.execute(
                        "SELECT deposito_id FROM estoque_parametro WHERE produto_id=? AND ativo ORDER BY id LIMIT 1",
                        (produto_id,),
                    ).fetchone()
                    deposito_id = int(row["deposito_id"]) if row else None
                if deposito_id is None:
                    row = conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()
                    deposito_id = int(row["id"]) if row else None
            ids = [(produto_id, deposito_id)]
        else:
            sql = (
                "SELECT produto_id, deposito_id FROM estoque_saldo"
                " WHERE quantidade<>0 OR reserva<>0"
                " UNION SELECT produto_id, deposito_id FROM estoque_parametro WHERE ativo"
                " UNION SELECT DISTINCT produto_id, (SELECT id FROM depositos ORDER BY id LIMIT 1) AS deposito_id"
                "   FROM orcamento_itens oi JOIN orcamentos o ON o.id=oi.orcamento_id"
                "   WHERE o.status='finalizado'"
                "     AND SUBSTR(o.criado_em,1,10) >= to_char(CURRENT_DATE - interval '6 month', 'YYYY-MM-DD')"
            )
            if deposito_id:
                sql = f"SELECT * FROM ({sql}) t WHERE deposito_id=?"
            rows = conn.execute(sql, (deposito_id,) if deposito_id else ()).fetchall()
            ids = [(r["produto_id"], r["deposito_id"]) for r in rows]

        produtos = {}
        for pid in {p for p, _ in ids}:
            r = conn.execute("SELECT id, nome, sku, unidade_venda, fator_conversao, custo_unitario FROM produtos_cadastro WHERE id=?", (pid,)).fetchone()
            if r:
                produtos[pid] = r

        sugestoes = []
        hoje = date.today()
        for pid, dep in ids:
            if pid not in produtos:
                continue
            p = produtos[pid]
            if not dep:
                continue
            s = _saldo(conn, dep, pid)
            disponivel = s["fisico"] - s["reservado"] - s["bloqueado"] - s["separacao"]
            transito = _transito(conn, pid)
            demanda_aberta = _demanda_aberta(conn, pid)
            disponivel_projetado = disponivel + transito - demanda_aberta

            par = parametro_svc.obter_efetivo(pid, dep)
            minimo = float(par.get("minimo") or 0)
            maximo = float(par.get("maximo") or 0)
            seguranca = float(par.get("estoque_seguranca") or 0)
            ponto = float(par.get("ponto_pedido") or 0) if par.get("ponto_pedido") else None
            lead_dias = int(par["lead_time_dias"]) if par.get("lead_time_dias") else None
            lote_min = float(par.get("lote_minimo") or 0)
            lote_max = float(par.get("lote_maximo") or 0)
            lote_mult = float(par.get("lote_multiplo") or 0)
            politica = par.get("politica") or "manual"

            f = _fornecedor(conn, pid)
            if lead_dias is None and f:
                lead_dias = _fornecedor_lead_time(conn, f["fornecedor_id"]) or 0
            lead_dias = lead_dias or 0

            demanda_mensal = _demanda_mensal(conn, pid)
            demanda_lead = demanda_mensal * lead_dias / 30.0 if lead_dias else 0.0
            alvo = maximo if maximo > 0 else (minimo + seguranca)
            necessidade = max(0.0, alvo + demanda_lead - disponivel_projetado)

            # data provável de ruptura (demanda diária média)
            media_diaria = demanda_mensal / 30.0
            ruptura = None
            if media_diaria > 0 and disponivel_projetado >= 0:
                dias = int(disponivel_projetado / media_diaria)
                ruptura = (hoje + timedelta(days=dias)).isoformat()

            # arredondamento: múltiplo do lote (respeita unidade de compra/fator)
            bruta = necessidade
            if necessidade > 0 and lote_mult > 0:
                import math
                bruta = math.ceil(necessidade / lote_mult) * lote_mult
            elif lote_min > 0:
                bruta = max(necessidade, lote_min)
            if lote_max > 0:
                bruta = min(bruta, lote_max)

            # não duplica: se o trânsito já cobre, necessidade = 0
            if transito >= alvo + demanda_lead:
                bruta = 0.0

            sobe_encomenda = politica == "sob_encomenda"
            if sobe_encomenda:
                bruta = 0.0

            trigger = ponto is not None and disponivel_projetado <= ponto
            sugestoes.append({
                "produto_id": pid, "sku": p["sku"], "nome": p["nome"],
                "unidade_venda": p["unidade_venda"] or "UN",
                "deposito_id": dep,
                "fisico": round(s["fisico"], 3), "reservado": round(s["reservado"], 3),
                "bloqueado": round(s["bloqueado"], 3),
                "disponivel": round(disponivel, 3),
                "transito": round(transito, 3), "demanda_aberta": round(demanda_aberta, 3),
                "disponivel_projetado": round(disponivel_projetado, 3),
                "estoque_alvo": round(alvo, 3), "estoque_seguranca": round(seguranca, 3),
                "demanda_lead_time": round(demanda_lead, 3),
                "lead_time_dias": lead_dias,
                "necessidade": round(necessidade, 3),
                "sugestao": round(bruta, 3),
                "ponto_pedido": ponto, "politica": politica,
                "ruptura_provavel": ruptura,
                "fornecedor_id": f["fornecedor_id"] if f else None,
                "fornecedor_nome": f["fornecedor_nome"] if f else None,
                "ultimo_preco": float(f["ultimo_preco"]) if f and f["ultimo_preco"] else None,
                "trigger_ponto_pedido": trigger,
                "sob_encomenda": sobe_encomenda,
                "justificativa": _justificativa(disponivel_projetado, alvo, demanda_lead, transito, demanda_aberta),
            })

    sugestoes.sort(key=lambda s: s["ruptura_provavel"] or "9999", reverse=False)
    return {
        "data": hoje.isoformat(),
        "sugestoes": sugestoes,
        "resumo": {
            "com_necessidade": sum(1 for s in sugestoes if s["sugestao"] > 0),
            "total_sugerido": round(sum(s["sugestao"] for s in sugestoes), 3),
        },
    }


def _justificativa(disp_proj: float, alvo: float, demanda_lead: float, transito: float, demanda_aberta: float) -> str:
    partes = [
        f"disponível projetado {disp_proj:g}",
        f"alvo {alvo:g}",
        f"demanda no lead time {demanda_lead:g}",
    ]
    if transito:
        partes.append(f"em trânsito {transito:g}")
    if demanda_aberta:
        partes.append(f"demanda aberta {demanda_aberta:g}")
    return " — ".join(partes)