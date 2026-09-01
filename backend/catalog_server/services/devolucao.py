"""Devolução ao fornecedor (REC-006): vinculada ao recebimento/NF/lote, com
saída de estoque, crédito/estorno a pagar e auditoria. Não devolve mais que o
recebido; lote é rastreado.
"""

from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories.estoque import estoque_repo

MOTIVOS = ("avariado", "erro_quantidade", "nao_conforme", "devolucao_comercial", "outro")
ESTADOS = ("avariado", "novo", "usado", "incompleto")


def criar(recebimento_id: int, motivo: str, estado: str = "avariado", documento_fiscal: str | None = None,
          observacao: str | None = None, usuario_id: int | None = None, itens: list[dict] | None = None) -> dict:
    motivo = (motivo or "").strip().lower()
    estado = (estado or "avariado").strip().lower()
    if motivo not in MOTIVOS:
        raise ValueError(f"motivo inválido (use: {', '.join(MOTIVOS)})")
    if estado not in ESTADOS:
        raise ValueError(f"estado inválido (use: {', '.join(ESTADOS)})")
    itens = itens or []
    if not itens:
        raise ValueError("itens da devolução são obrigatórios")

    with system_conn() as conn:
        rec = conn.execute(
            "SELECT * FROM recebimento WHERE id=?", (recebimento_id,)
        ).fetchone()
        if not rec:
            raise LookupError("Recebimento não encontrado")
        if rec["status"] != "finalizado":
            raise ValueError("Devolução exige recebimento finalizado")

        # não devolve mais que o recebido (por produto, soma dos recebimentos finalizados)
        aceitos = {}
        for r in conn.execute(
            "SELECT r.produto_id, SUM(r.qtd_aceita) AS qtd"
            " FROM recebimento_item r JOIN recebimento rc ON rc.id=r.recebimento_id"
            " WHERE rc.pedido_id=? AND rc.status='finalizado' GROUP BY r.produto_id",
            (rec["pedido_id"],),
        ).fetchall():
            aceitos[int(r["produto_id"])] = float(r["qtd"] or 0)

        dev_id = conn.execute(
            "INSERT INTO devolucao_fornecedor (recebimento_id, pedido_id, fornecedor_id, documento_fiscal,"
            " motivo, estado, observacao, status, usuario_id)"
            " VALUES (?,?,?,?,?,?,?, 'aberta', ?) RETURNING id",
            (recebimento_id, rec["pedido_id"], rec["fornecedor_id"], (documento_fiscal or "").strip() or None,
             motivo, estado, observacao, usuario_id),
        ).fetchone()["id"]

        for it in itens:
            pid = int(it["produto_id"])
            qtd = float(it.get("quantidade") or 0)
            if qtd <= 0:
                raise ValueError("quantidade deve ser positiva")
            # não devolve mais que o aceito no recebimento
            if qtd > aceitos.get(pid, 0):
                raise ValueError(f"Não é possível devolver mais que o recebido (produto {pid}: {aceitos.get(pid, 0):g})")
            lote_id = it.get("lote_id")
            if lote_id:
                lote = conn.execute(
                    "SELECT 1 FROM lotes WHERE id=? AND produto_id=?", (lote_id, pid)
                ).fetchone()
                if not lote:
                    raise ValueError(f"Lote {lote_id} não pertence ao produto {pid}")
            conn.execute(
                "INSERT INTO devolucao_fornecedor_item (devolucao_id, produto_id, lote_id, quantidade)"
                " VALUES (?,?,?,?)",
                (dev_id, pid, lote_id, qtd),
            )
            # reserva a quantidade devolvida (não pode ser usada em outra devolução)
            aceitos[pid] -= qtd
    return {"devolucao_id": dev_id, "pedido_id": rec["pedido_id"], "itens": len(itens)}


def concluir(devolucao_id: int, usuario_id: int | None = None) -> dict:
    """Efeitos: saída de estoque (com lote), crédito/estorno a pagar e status concluída."""
    from datetime import datetime, timedelta

    with system_conn() as conn:
        dev = conn.execute(
            "SELECT * FROM devolucao_fornecedor WHERE id=?", (devolucao_id,)
        ).fetchone()
        if not dev:
            raise LookupError("Devolução não encontrada")
        if dev["status"] != "aberta":
            raise ValueError(f"Devolução {dev['status']} não pode ser concluída")
        itens = conn.execute(
            "SELECT * FROM devolucao_fornecedor_item WHERE devolucao_id=?",
            (devolucao_id,),
        ).fetchall()
        total = 0.0
        for it in itens:
            qtd = float(it["quantidade"])
            preco = conn.execute(
                "SELECT pi.preco_unitario FROM pedido_itens pi"
                " JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id"
                " WHERE ci.produto_id=? AND pi.pedido_id=? LIMIT 1",
                (it["produto_id"], dev["pedido_id"]),
            ).fetchone()
            preco_u = float(preco["preco_unitario"] or 0) if preco else 0.0
            total += qtd * preco_u
            estoque_repo.movimentar_fato(
                conn.execute("SELECT deposito_id FROM recebimento WHERE id=?", (dev["recebimento_id"],)).fetchone()["deposito_id"],
                it["produto_id"], "saida", qtd,
                idempotency_key=f"devolucao-{devolucao_id}-item-{it['id']}",
                origem_tipo="devolucao_fornecedor", origem_id=devolucao_id,
                documento=dev["documento_fiscal"],
                lote_id=it["lote_id"],
                observacao=f"devolução ao fornecedor #{devolucao_id}",
                usuario_id=usuario_id, _conn=conn,
            )
        # crédito/estorno a pagar (conta negativa vinculada ao pedido)
        venc = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO contas_pagar (descricao, fornecedor_id, valor, saldo, data_vencimento, status,"
            " origem_tipo, origem_id) VALUES (?,?,?,?,?, 'aberto', 'devolucao_fornecedor', ?)",
            (f"Devolução #{devolucao_id} — crédito", dev["fornecedor_id"],
             -round(total, 2), -round(total, 2), venc, dev["pedido_id"]),
        )
        conn.execute("UPDATE devolucao_fornecedor SET status='concluida' WHERE id=?", (devolucao_id,))
    return {"devolucao_id": devolucao_id, "total_creditado": round(total, 2), "itens": len(itens)}


def cancelar(devolucao_id: int) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE devolucao_fornecedor SET status='cancelada' WHERE id=? AND status='aberta'",
            (devolucao_id,),
        )
        return cur.rowcount > 0


def listar(pedido_id: int | None = None) -> list[dict]:
    sql = (
        "SELECT d.*, f.nome AS fornecedor_nome, r.documento_fiscal AS rec_doc"
        " FROM devolucao_fornecedor d"
        " LEFT JOIN fornecedores f ON f.id=d.fornecedor_id"
        " LEFT JOIN recebimento r ON r.id=d.recebimento_id"
    )
    args: list = []
    if pedido_id:
        sql += " WHERE d.pedido_id=?"
        args.append(pedido_id)
    sql += " ORDER BY d.id DESC"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def detalhe(devolucao_id: int) -> dict | None:
    with system_conn() as conn:
        dev = conn.execute(
            "SELECT d.*, f.nome AS fornecedor_nome FROM devolucao_fornecedor d"
            " LEFT JOIN fornecedores f ON f.id=d.fornecedor_id WHERE d.id=?",
            (devolucao_id,),
        ).fetchone()
        if not dev:
            return None
        itens = [dict(r) for r in conn.execute(
            "SELECT i.*, p.sku, p.nome AS produto_nome, l.codigo AS lote"
            " FROM devolucao_fornecedor_item i"
            " JOIN produtos_cadastro p ON p.id=i.produto_id"
            " LEFT JOIN lotes l ON l.id=i.lote_id WHERE i.devolucao_id=?",
            (devolucao_id,),
        ).fetchall()]
        out = dict(dev)
        out["itens"] = itens
        return out