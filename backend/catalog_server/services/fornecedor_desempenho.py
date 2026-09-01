"""Desempenho real do fornecedor (COM-005): lead time médio/desvio, fill rate,
preço líquido, indisponibilidade e atraso a partir dos pedidos. Override manual
com motivo. Confiança baixa quando pouca amostra.
"""

from __future__ import annotations

import statistics

from catalog_server.db import system_conn

AMOSTRA_MINIMA = 5


def calcular(fornecedor_id: int, data_inicio: str | None = None, data_fim: str | None = None) -> dict:
    with system_conn() as conn:
        f = conn.execute(
            "SELECT id, nome, prazo_entrega_dias, lead_time_override, lead_time_override_motivo"
            " FROM fornecedores WHERE id=?",
            (fornecedor_id,),
        ).fetchone()
        if not f:
            raise LookupError("Fornecedor não encontrado")
        sql = (
            "SELECT pc.id, pc.data_geracao, pc.data_prometida, pc.data_enviada,"
            " pc.data_recebida, pc.status,"
            " COALESCE(AVG(pi.preco_unitario),0) AS preco_medio, COUNT(pi.id) AS itens,"
            " pc.data_geracao::timestamp AS geracao_ts,"
            " pc.data_recebida::timestamp AS recebida_ts,"
            " pc.data_prometida::timestamp AS prometida_ts"
            " FROM pedidos_compra pc"
            " LEFT JOIN pedido_itens pi ON pi.pedido_id=pc.id"
            " WHERE pc.fornecedor_id=?"
        )
        args: list = [fornecedor_id]
        if data_inicio:
            sql += " AND COALESCE(pc.data_recebida, pc.data_geracao)::date >= ?"
            args.append(data_inicio)
        if data_fim:
            sql += " AND COALESCE(pc.data_recebida, pc.data_geracao)::date <= ?"
            args.append(data_fim)
        sql += " GROUP BY pc.id ORDER BY pc.id DESC"
        pedidos = [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]

    lead_times: list[float] = []
    atrasos: list[float] = []
    recebidos = 0
    total_itens = 0
    for p in pedidos:
        if p["recebida_ts"] and p["geracao_ts"]:
            lt = (p["recebida_ts"] - p["geracao_ts"]).days
            lead_times.append(float(lt))
            if p["prometida_ts"]:
                atraso = (p["recebida_ts"] - p["prometida_ts"]).days
                atrasos.append(float(atraso))
        if p["status"] == "recebido":
            recebidos += 1
        total_itens += int(p["itens"] or 0)

    n = len(pedidos)
    lead_time_medio = round(statistics.mean(lead_times), 2) if lead_times else None
    lead_time_desvio = round(statistics.pstdev(lead_times), 2) if len(lead_times) > 1 else None
    fill_rate = round(recebidos / n, 4) if n else None
    atraso_medio = round(statistics.mean(atrasos), 2) if atrasos else None
    confianca = "alta" if n >= AMOSTRA_MINIMA else ("media" if n >= 3 else "baixa")

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO fornecedor_desempenho (fornecedor_id, data_inicio, data_fim, n_pedidos,"
            " lead_time_medio, lead_time_desvio, fill_rate, atraso_medio_dias, confianca)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (fornecedor_id, data_inicio, data_fim, n, lead_time_medio, lead_time_desvio,
             fill_rate, atraso_medio, confianca),
        )

    return {
        "fornecedor_id": fornecedor_id,
        "fornecedor_nome": f["nome"],
        "n_pedidos": n,
        "lead_time_medio": lead_time_medio,
        "lead_time_desvio": lead_time_desvio,
        "fill_rate": fill_rate,
        "atraso_medio_dias": atraso_medio,
        "confianca": confianca,
        "prazo_contratual": f["prazo_entrega_dias"],
        "lead_time_override": f["lead_time_override"],
        "lead_time_override_motivo": f["lead_time_override_motivo"],
        "lead_time_efetivo": f["lead_time_override"] or (lead_time_medio if lead_time_medio is not None and confianca != "baixa" else None) or f["prazo_entrega_dias"],
        "pedidos": pedidos,
    }


def set_override(fornecedor_id: int, lead_time_dias: int | None, motivo: str | None, usuario_id: int | None = None) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE fornecedores SET lead_time_override=?, lead_time_override_motivo=? WHERE id=?",
            (lead_time_dias, (motivo or "").strip() or None, fornecedor_id),
        )
        return cur.rowcount > 0


def historico(fornecedor_id: int) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM fornecedor_desempenho WHERE fornecedor_id=? ORDER BY id DESC LIMIT 20",
            (fornecedor_id,),
        ).fetchall()]