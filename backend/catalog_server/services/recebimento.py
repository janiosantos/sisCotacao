"""Documento de recebimento (REC-001): conferência parcial, recebimentos
múltiplos do mesmo pedido sem ultrapassar saldo, retry idempotente, entrada de
estoque + contas a pagar só dos aceitos, pedido atualiza status.
"""

from __future__ import annotations

from datetime import date

from catalog_server.db import system_conn
from catalog_server.repositories.estoque import estoque_repo


def criar(pedido_id: int, deposito_id: int = 1, documento_fiscal: str | None = None,
          operador_id: int | None = None) -> dict:
    with system_conn() as conn:
        pedido = conn.execute("SELECT * FROM pedidos_compra WHERE id=?", (pedido_id,)).fetchone()
        if not pedido:
            raise LookupError("Pedido não encontrado")
        if pedido["status"] == "recebido":
            raise ValueError("Pedido já recebido por completo")
        if pedido["status"] == "cancelado":
            raise ValueError("Pedido cancelado não pode ser recebido")

        if documento_fiscal:
            existente = conn.execute(
                "SELECT id FROM recebimento WHERE pedido_id=? AND documento_fiscal=?",
                (pedido_id, documento_fiscal),
            ).fetchone()
            if existente:
                return {"recebimento_id": existente["id"], "duplicado": True}

        itens = conn.execute(
            "SELECT pi.*, ci.produto_id, p.unidade_venda"
            " FROM pedido_itens pi JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id"
            " JOIN produtos_cadastro p ON p.id=ci.produto_id WHERE pi.pedido_id=?",
            (pedido_id,),
        ).fetchall()
        if not itens:
            raise ValueError("Pedido sem itens")

        rec_id = conn.execute(
            "INSERT INTO recebimento (pedido_id, fornecedor_id, deposito_id, operador_id,"
            " documento_fiscal, data_recebimento, status)"
            " VALUES (?,?,?,?,?,?, 'aberto') RETURNING id",
            (pedido_id, pedido["fornecedor_id"], deposito_id, operador_id,
             (documento_fiscal or "").strip() or None, date.today().isoformat()),
        ).fetchone()["id"]
        for it in itens:
            conn.execute(
                "INSERT INTO recebimento_item (recebimento_id, pedido_item_id, produto_id,"
                " qtd_pedido, qtd_recebida, status)"
                " VALUES (?,?,?,?,0, 'pendente')",
                (rec_id, it["id"], it["produto_id"], it["quantidade"]),
            )
    return {"recebimento_id": rec_id, "duplicado": False, "itens": len(itens)}


def conferir_item(recebimento_id: int, item_id: int, qtd_aceita: float, qtd_recusada: float = 0,
                  qtd_avariada: float = 0) -> dict:
    qa, qr, qv = float(qtd_aceita or 0), float(qtd_recusada or 0), float(qtd_avariada or 0)
    with system_conn() as conn:
        rec = conn.execute("SELECT status FROM recebimento WHERE id=?", (recebimento_id,)).fetchone()
        if not rec:
            raise LookupError("Recebimento não encontrado")
        if rec["status"] != "aberto":
            raise ValueError(f"Recebimento {rec['status']} não aceita conferência")
        item = conn.execute(
            "SELECT * FROM recebimento_item WHERE id=? AND recebimento_id=?",
            (item_id, recebimento_id),
        ).fetchone()
        if not item:
            raise LookupError("Item de recebimento não encontrado")
        # não ultrapassa o saldo do pedido (soma dos recebimentos já finalizados)
        saldo = float(item["qtd_pedido"] or 0)
        recebido_antes = float(item["qtd_recebida"] or 0)
        # aceita + recusada + avariada ≤ quantidade que ainda resta do pedido + o já recebido aqui
        total = qa + qr + qv
        limite_pedido = saldo
        # já recebido globalmente (outros recebimentos) via soma
        global_rec = conn.execute(
            "SELECT COALESCE(SUM(r.qtd_aceita + r.qtd_recusada + r.qtd_avariada),0) AS soma"
            " FROM recebimento_item r JOIN recebimento rc ON rc.id=r.recebimento_id"
            " WHERE r.produto_id=? AND rc.pedido_id=(SELECT pedido_id FROM recebimento WHERE id=?)"
            " AND rc.status IN ('finalizado','conferido')",
            (item["produto_id"], recebimento_id),
        ).fetchone()["soma"]
        if float(global_rec or 0) + total > limite_pedido:
            raise ValueError(
                f"Quantidade excede o saldo do pedido (restam {max(limite_pedido - float(global_rec or 0), 0):g})"
            )
        status = "aceito" if qa > 0 and qr == 0 and qv == 0 else ("recusado" if qr > 0 else "avariado")
        conn.execute(
            "UPDATE recebimento_item SET qtd_recebida=?, qtd_aceita=?, qtd_recusada=?, qtd_avariada=?, status=?"
            " WHERE id=?",
            (qa + qr + qv, qa, qr, qv, status, item_id),
        )
        pendentes = conn.execute(
            "SELECT COUNT(*) FROM recebimento_item WHERE recebimento_id=? AND status='pendente'",
            (recebimento_id,),
        ).fetchone()["count"]
        if pendentes == 0:
            conn.execute("UPDATE recebimento SET status='conferido' WHERE id=?", (recebimento_id,))
        return {"item_id": item_id, "status": status, "pendentes": pendentes}


def finalizar(recebimento_id: int, condicao_pagamento_id: int | None = None, usuario_id: int | None = None) -> dict:
    """Aplica estoque + contas a pagar dos aceitos e atualiza o status do pedido."""
    from catalog_server.repositories import compras_repo

    with system_conn() as conn:
        rec = conn.execute("SELECT * FROM recebimento WHERE id=?", (recebimento_id,)).fetchone()
        if not rec:
            raise LookupError("Recebimento não encontrado")
        if rec["status"] != "conferido":
            raise ValueError(f"Recebimento {rec['status']} deve estar conferido para finalizar")
        # REC-003: divergência de três vias precisa de aprovação para efeitos definitivos
        if (rec["status_tres_vias"] or "aguardando_conferencia") == "divergente":
            raise ValueError("Divergência de três vias precisa de aprovação antes de finalizar")
        if (rec["status_tres_vias"] or "") == "rejeitado":
            raise ValueError("Recebimento rejeitado não pode ser finalizado")
        itens = conn.execute(
            "SELECT * FROM recebimento_item WHERE recebimento_id=? AND qtd_aceita > 0",
            (recebimento_id,),
        ).fetchall()
        if not itens:
            raise ValueError("Nenhum item aceito para receber")

        total = 0.0
        for it in itens:
            qa = float(it["qtd_aceita"])
            preco = conn.execute(
                "SELECT preco_unitario FROM pedido_itens WHERE id=?", (it["pedido_item_id"],)
            ).fetchone()["preco_unitario"]
            total += qa * float(preco or 0)
            estoque_repo.movimentar_fato(
                rec["deposito_id"], it["produto_id"], "entrada", qa,
                idempotency_key=f"rec-{recebimento_id}-item-{it['id']}",
                origem_tipo="pedido_compra", origem_id=rec["pedido_id"],
                documento=rec["documento_fiscal"], custo_unitario=float(preco or 0),
                observacao=f"recebimento #{recebimento_id}",
                usuario_id=usuario_id, _conn=conn,
            )
            conn.execute(
                "UPDATE recebimento_item SET status='recebido' WHERE id=? AND status='aceito'",
                (it["id"],),
            )

        # contas a pagar (simplificado: 1 conta em 30 dias; condição via compras_repo quando aplicável)
        from catalog_server.repositories.financeiro import contas_repo
        from datetime import datetime, timedelta

        venc = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        fornecedor = conn.execute("SELECT nome FROM fornecedores WHERE id=?", (rec["fornecedor_id"],)).fetchone()
        conn.execute(
            "INSERT INTO contas_pagar (descricao, fornecedor_id, valor, saldo, data_vencimento, status,"
            " origem_tipo, origem_id) VALUES (?,?,?,?,?, 'aberto', 'pedido_compra', ?)",
            (f"Recebimento #{recebimento_id} — {fornecedor['nome'] if fornecedor else ''}", rec["fornecedor_id"],
             round(total, 2), round(total, 2), venc, rec["pedido_id"]),
        )

        # atualiza status do pedido (recebido se não resta nada; senão parcialmente_recebido)
        pedido_total = conn.execute(
            "SELECT COALESCE(SUM(ci.quantidade),0) AS total FROM pedido_itens pi"
            " JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id WHERE pi.pedido_id=?",
            (rec["pedido_id"],),
        ).fetchone()["total"]
        recebido_total = conn.execute(
            "SELECT COALESCE(SUM(r.qtd_aceita + r.qtd_recusada + r.qtd_avariada),0) AS soma"
            " FROM recebimento_item r JOIN recebimento rc ON rc.id=r.recebimento_id"
            " WHERE rc.pedido_id=? AND rc.status IN ('finalizado','conferido')",
            (rec["pedido_id"],),
        ).fetchone()["soma"]
        novo_status = "recebido" if float(recebido_total or 0) >= float(pedido_total or 0) else "parcialmente_recebido"
        conn.execute("UPDATE pedidos_compra SET status=? WHERE id=?", (novo_status, rec["pedido_id"]))
        conn.execute("UPDATE recebimento SET status='finalizado' WHERE id=?", (recebimento_id,))
    return {"recebimento_id": recebimento_id, "pedido_status": novo_status, "total": round(total, 2),
            "itens_aceitos": len(itens)}


def detalhe(recebimento_id: int) -> dict | None:
    with system_conn() as conn:
        rec = conn.execute(
            "SELECT r.*, p.numero AS pedido, f.nome AS fornecedor_nome, u.nome AS operador_nome"
            " FROM recebimento r"
            " LEFT JOIN pedidos_compra p ON p.id=r.pedido_id"
            " LEFT JOIN fornecedores f ON f.id=r.fornecedor_id"
            " LEFT JOIN usuarios u ON u.id=r.operador_id WHERE r.id=?",
            (recebimento_id,),
        ).fetchone()
        if not rec:
            return None
        itens = [dict(r) for r in conn.execute(
            "SELECT i.*, pr.sku, pr.nome AS produto_nome, pr.unidade_venda"
            " FROM recebimento_item i JOIN produtos_cadastro pr ON pr.id=i.produto_id"
            " WHERE i.recebimento_id=? ORDER BY i.id",
            (recebimento_id,),
        ).fetchall()]
        out = dict(rec)
        out["itens"] = itens
        return out


def listar(pedido_id: int | None = None) -> list[dict]:
    with system_conn() as conn:
        sql = (
            "SELECT r.*, p.numero AS pedido, f.nome AS fornecedor_nome"
            " FROM recebimento r LEFT JOIN pedidos_compra p ON p.id=r.pedido_id"
            " LEFT JOIN fornecedores f ON f.id=r.fornecedor_id"
        )
        args: list = []
        if pedido_id:
            sql += " WHERE r.pedido_id=?"
            args.append(pedido_id)
        sql += " ORDER BY r.id DESC"
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]