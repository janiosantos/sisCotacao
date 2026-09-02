"""Parcelas de venda (v2.22.0): geração de contas a receber por condição.

Regras:
- Só gera parcelas quando o orçamento tem CLIENTE IDENTIFICADO (não é o
  cliente padrão CONSUMIDOR id=1) E uma condição de pagamento ATIVA.
- Condição sem parcelas ou com 1 parcela de 0 dias = À VISTA (balcão/caixa).
- Condição com >= 2 parcelas (ou 1 parcela com dias > 0) = A PRAZO: gera N
  contas a receber, uma por parcela, com vencimento = hoje + dias.
- Reabrir/cancelar estorna as contas a receber do documento.
"""
from __future__ import annotations

from datetime import date, timedelta

from catalog_server.db import system_conn
from catalog_server.repositories import condicao_repo, contas_repo

# Cliente padrão (balcão) nunca gera parcelas.
CLIENTE_PADRAO_ID = 1


def eh_cliente_identificado(cliente_id: int | None) -> bool:
    return cliente_id is not None and int(cliente_id) != CLIENTE_PADRAO_ID


def condicao_ativa(condicao_id: int | None, _conn=None) -> bool:
    if not condicao_id:
        return False
    cond = condicao_repo.get(int(condicao_id), _conn=_conn)
    return bool(cond and cond.get("ativo"))


def eh_a_prazo(condicao_id: int | None, _conn=None) -> bool:
    """True quando a condição tem parcelas além de 'à vista' (>=2 ou 1 com dias)."""
    if not condicao_ativa(condicao_id, _conn=_conn):
        return False
    parcelas = condicao_repo.list_parcelas(int(condicao_id), _conn=_conn)
    if not parcelas:
        return False
    if len(parcelas) >= 2:
        return True
    return int(parcelas[0].get("dias") or 0) > 0


def gerar_contas_receber(orcamento: dict, _conn=None) -> list[dict]:
    """Gera contas a receber por parcela quando aplicável.

    Retorna as parcelas criadas; lista vazia quando é à vista/sem condição.
    """
    if not eh_cliente_identificado(orcamento.get("cliente_id")):
        return []
    condicao_id = orcamento.get("condicao_pagamento_id")
    if not condicao_ativa(condicao_id, _conn=_conn):
        return []
    parcelas = condicao_repo.list_parcelas(int(condicao_id), _conn=_conn)
    if not parcelas:
        return []

    total = float(orcamento.get("total") or 0)
    numero = str(orcamento.get("numero") or "")
    cliente = orcamento.get("cliente") or ""
    hoje = date.today()
    criadas: list[dict] = []
    soma_pct = 0.0
    from catalog_server.services.lancamentos_lote import novo_grupo

    grupo = novo_grupo()
    n = len(parcelas)

    for i, p in enumerate(parcelas, start=1):
        pct = float(p.get("percentual") or 0)
        soma_pct += pct
        dias = int(p.get("dias") or 0)
        valor = round(total * pct / 100.0, 2)
        if valor <= 0:
            continue
        venc = (hoje + timedelta(days=dias)).isoformat()
        conta_id = contas_repo.criar_receber(
            cliente=cliente,
            cliente_id=int(orcamento["cliente_id"]),
            valor=valor,
            data_vencimento=venc,
            descricao=f"Venda {numero} — parcela {i}/{n}",
            documento=numero,
            observacao=f"Parcela {i}/{n} · condição de pagamento",
            _conn=_conn,
        )
        if _conn is None:
            with system_conn() as conn:
                conn.execute(
                    "UPDATE contas_receber SET origem_tipo='venda', origem_id=?,"
                    " parcela=?, total_parcelas=?, grupo_id=? WHERE id=?",
                    (orcamento.get("id"), i, n, grupo, conta_id),
                )
        else:
            _conn.execute(
                "UPDATE contas_receber SET origem_tipo='venda', origem_id=?,"
                " parcela=?, total_parcelas=?, grupo_id=? WHERE id=?",
                (orcamento.get("id"), i, n, grupo, conta_id),
            )
        criadas.append({
            "conta_id": conta_id,
            "parcela": i,
            "total_parcelas": n,
            "dias": dias,
            "vencimento": venc,
            "valor": valor,
        })

    # Se as parcelas não somam 100%, ajusta a última para cobrir a diferença.
    if criadas and abs(soma_pct - 100.0) > 0.005:
        dif = round(total - sum(c["valor"] for c in criadas), 2)
        if abs(dif) > 0.005:
            if _conn is None:
                with system_conn() as conn:
                    conn.execute(
                        "UPDATE contas_receber SET valor=?, saldo=? WHERE id=?",
                        (criadas[-1]["valor"] + dif, criadas[-1]["valor"] + dif, criadas[-1]["conta_id"]),
                    )
            else:
                _conn.execute(
                    "UPDATE contas_receber SET valor=?, saldo=? WHERE id=?",
                    (criadas[-1]["valor"] + dif, criadas[-1]["valor"] + dif, criadas[-1]["conta_id"]),
                )
            criadas[-1]["valor"] = round(criadas[-1]["valor"] + dif, 2)

    return criadas


def estornar_contas_receber(orcamento: dict, _conn=None) -> int:
    """Estorna (cancela) as contas a receber do documento do orçamento.

    Retorna quantas contas foram estornadas.
    """
    numero = str(orcamento.get("numero") or "")
    if not numero:
        return 0
    if _conn is None:
        with system_conn() as conn:
            return estornar_contas_receber(orcamento, _conn=conn)

    rows = _conn.execute(
            "SELECT id FROM contas_receber WHERE documento=? AND status IN ('aberto','parcial')",
            (numero,),
        ).fetchall()
    for r in rows:
        _conn.execute(
            "UPDATE contas_receber SET status='cancelado' WHERE id=?",
            (r["id"],),
        )
    return len(rows)
