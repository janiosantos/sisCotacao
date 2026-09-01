"""Reconciliação e divergências (ARC-005): jobs/relatórios de divergência com
severidade, origem, data e ação. Correção é comando auditado, não SQL manual.
"""

from __future__ import annotations

from catalog_server.db import system_conn


def divergencias() -> dict:
    """Consolida divergências do ERP por categoria."""
    with system_conn() as conn:
        pedido_sem_movimento = [dict(r) for r in conn.execute(
            """SELECT pc.id, pc.numero, pc.status, pc.criado_em
               FROM pedidos_compra pc
               WHERE pc.status NOT IN ('cancelado')
                 AND NOT EXISTS (SELECT 1 FROM estoque_movimento m
                                 WHERE m.origem_tipo='pedido_compra' AND m.origem_id=pc.id)
               ORDER BY pc.id DESC LIMIT 50"""
        ).fetchall()]
        movimento_sem_origem = [dict(r) for r in conn.execute(
            """SELECT m.id, m.tipo, m.quantidade, m.criado_em, m.origem_tipo
               FROM estoque_movimento m
               WHERE (m.origem_tipo IS NULL OR m.origem_tipo='')
                 AND m.tipo NOT IN ('reserva','liberacao')
               ORDER BY m.id DESC LIMIT 50"""
        ).fetchall()]
        saldo_inconsistente = [dict(r) for r in conn.execute(
            """SELECT s.deposito_id, s.produto_id, s.quantidade,
                      (SELECT COALESCE(SUM(CASE WHEN m.tipo IN ('entrada','inventario') THEN m.quantidade
                                               WHEN m.tipo IN ('saida','transferencia','ajuste') THEN -m.quantidade
                                               ELSE 0 END),0)
                       FROM estoque_movimento m WHERE m.deposito_id=s.deposito_id AND m.produto_id=s.produto_id) AS soma_ledger,
                      s.quantidade - (SELECT COALESCE(SUM(CASE WHEN m.tipo IN ('entrada','inventario') THEN m.quantidade
                                               WHEN m.tipo IN ('saida','transferencia','ajuste') THEN -m.quantidade
                                               ELSE 0 END),0)
                       FROM estoque_movimento m WHERE m.deposito_id=s.deposito_id AND m.produto_id=s.produto_id) AS diferenca
               FROM estoque_saldo s
               WHERE s.quantidade <> 0
               ORDER BY ABS(s.quantidade - (SELECT COALESCE(SUM(CASE WHEN m.tipo IN ('entrada','inventario') THEN m.quantidade
                                               WHEN m.tipo IN ('saida','transferencia','ajuste') THEN -m.quantidade
                                               ELSE 0 END),0)
                       FROM estoque_movimento m WHERE m.deposito_id=s.deposito_id AND m.produto_id=s.produto_id)) DESC
               LIMIT 50"""
        ).fetchall()]
        reserva_orfã = [dict(r) for r in conn.execute(
            """SELECT m.id, m.produto_id, m.quantidade, m.criado_em
               FROM estoque_movimento m
               WHERE m.tipo='reserva' AND m.criado_em::timestamp < NOW() - interval '30 days'
                 AND m.origem_tipo='venda'
                 AND NOT EXISTS (SELECT 1 FROM estoque_movimento l
                                 WHERE l.tipo='liberacao' AND l.produto_id=m.produto_id AND l.id>m.id)
               ORDER BY m.id DESC LIMIT 50"""
        ).fetchall()]
        outbox_morta = [dict(r) for r in conn.execute(
            "SELECT id, topico, ultimo_erro, criado_em FROM outbox WHERE status='morta' ORDER BY id DESC LIMIT 50"
        ).fetchall()]

    def _serie(itens, severidade):
        return [{"severidade": severidade, "origem": item.pop("criado_em", None) if isinstance(item, dict) else None,
                 **item} for item in itens]

    return {
        "pedido_sem_movimento": _serie(pedido_sem_movimento, "alta"),
        "movimento_sem_origem": _serie(movimento_sem_origem, "alta"),
        "saldo_inconsistente": _serie(saldo_inconsistente, "critica"),
        "reserva_orfã": _serie(reserva_orfã, "media"),
        "outbox_morta": _serie(outbox_morta, "media"),
        "resumo": {
            "pedido_sem_movimento": len(pedido_sem_movimento),
            "movimento_sem_origem": len(movimento_sem_origem),
            "saldo_inconsistente": len(saldo_inconsistente),
            "reserva_orfã": len(reserva_orfã),
            "outbox_morta": len(outbox_morta),
        },
    }