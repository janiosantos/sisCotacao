"""Pós-venda (POS-001/002): RMA/devolução vinculada à venda, troca com diferença
e crédito de cliente (sem duplicar, com origem).
"""

from __future__ import annotations

from datetime import date, timedelta

from catalog_server.db import system_conn
from catalog_server.repositories.estoque import estoque_repo

_RMA_TRANSICOES: dict[str, set[str]] = {
    "solicitada": {"autorizada", "rejeitada"},
    "autorizada": {"recebida", "rejeitada"},
    "recebida": {"analisada"},
    "analisada": {"concluida", "rejeitada"},
    "concluida": set(),
    "rejeitada": set(),
}


def solicitar(orcamento_id: int, produto_id: int, quantidade: float, motivo: str,
              condicao: str = "avariado", lote_id: int | None = None, observacao: str | None = None) -> dict:
    motivo = (motivo or "").strip().lower()
    if motivo not in ("defeito", "arrependimento", "entrega_errada", "avariado_transporte", "outro"):
        raise ValueError("motivo inválido")
    condicao = (condicao or "avariado").strip().lower()
    if condicao not in ("avariado", "novo", "usado", "incompleto"):
        raise ValueError("condição inválida")
    with system_conn() as conn:
        orc = conn.execute("SELECT * FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone()
        if not orc:
            raise LookupError("Orçamento não encontrado")
        if orc["status"] not in ("finalizado", "recebido"):
            raise ValueError(f"Orçamento {orc['status']} — RMA exige venda finalizada")
        vendido = conn.execute(
            "SELECT COALESCE(SUM(quantidade),0) AS qtd FROM orcamento_itens WHERE orcamento_id=? AND produto_id=?",
            (orcamento_id, produto_id),
        ).fetchone()["qtd"]
        if float(quantidade) > float(vendido or 0):
            raise ValueError(f"Devolução acima do vendido (vendeu {float(vendido or 0):g})")
        rma_id = conn.execute(
            "INSERT INTO rma (orcamento_id, cliente_id, produto_id, lote_id, quantidade, motivo,"
            " condicao, status, observacao) VALUES (?,?,?,?,?,?,?, 'solicitada', ?) RETURNING id",
            (orcamento_id, orc["cliente_id"], produto_id, lote_id, quantidade, motivo, condicao, observacao),
        ).fetchone()["id"]
    return {"rma_id": rma_id, "status": "solicitada"}


def transicionar(rma_id: int, novo_status: str, analise: str | None = None) -> dict:
    novo_status = (novo_status or "").strip().lower()
    with system_conn() as conn:
        r = conn.execute("SELECT * FROM rma WHERE id=?", (rma_id,)).fetchone()
        if not r:
            raise LookupError("RMA não encontrado")
        if novo_status not in _RMA_TRANSICOES.get(r["status"], set()):
            raise ValueError(f"Transição inválida: {r['status']} → {novo_status}")
        conn.execute(
            "UPDATE rma SET status=?, analise=? WHERE id=?",
            (novo_status, analise or r["analise"], rma_id),
        )
        # concluída → reposição de estoque (item volta) + crédito de cliente
        if novo_status == "concluida":
            _concluir_efeitos(conn, r)
    return {"rma_id": rma_id, "status": novo_status}


def _concluir_efeitos(conn, r) -> None:
    # entrada do item devolvido (reposição de estoque)
    if float(r["quantidade"] or 0) > 0:
        dep = conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()
        estoque_repo.movimentar_fato(
            dep["id"] if dep else 1,
            r["produto_id"], "entrada", float(r["quantidade"]),
            idempotency_key=f"rma-{r['id']}-reposicao",
            origem_tipo="rma", origem_id=r["id"], lote_id=r["lote_id"],
            observacao=f"retorno de RMA #{r['id']}", _conn=conn,
        )
    # crédito de cliente (não duplica via origem única)
    valor_venda = conn.execute(
        "SELECT preco_unitario FROM orcamento_itens"
        " WHERE orcamento_id=? AND produto_id=? LIMIT 1",
        (r["orcamento_id"], r["produto_id"]),
    ).fetchone()
    if valor_venda:
        valor_credito = round(float(valor_venda["preco_unitario"] or 0) * float(r["quantidade"] or 0), 2)
        conn.execute(
            "INSERT INTO credito_cliente (cliente_id, valor, saldo, origem, origem_id, status)"
            " VALUES (?,?,?, 'rma', ?, 'aberto') ON CONFLICT (origem, origem_id) DO NOTHING",
            (r["cliente_id"], valor_credito, valor_credito, r["id"]),
        )


def trocar(rma_id: int, produto_novo_id: int, quantidade_nova: float, preco_novo: float) -> dict:
    """Troca: item substituto com diferença financeira em crédito/estorno."""
    with system_conn() as conn:
        r = conn.execute("SELECT * FROM rma WHERE id=?", (rma_id,)).fetchone()
        if not r:
            raise LookupError("RMA não encontrado")
        if r["status"] != "autorizada":
            raise ValueError(f"RMA {r['status']} — troca exige autorização")
        original = conn.execute(
            "SELECT preco_unitario FROM orcamento_itens WHERE orcamento_id=? AND produto_id=? LIMIT 1",
            (r["orcamento_id"], r["produto_id"]),
        ).fetchone()
        valor_original = float(original["preco_unitario"] or 0) * float(r["quantidade"] or 0) if original else 0.0
        valor_novo = float(preco_novo) * float(quantidade_nova)
        diferenca = round(valor_novo - valor_original, 2)
        troca_id = conn.execute(
            "INSERT INTO troca (rma_id, produto_novo_id, quantidade_nova, diferenca, status)"
            " VALUES (?,?,?,?, 'aberta') RETURNING id",
            (rma_id, produto_novo_id, quantidade_nova, diferenca),
        ).fetchone()["id"]
        conn.execute("UPDATE rma SET status='concluida' WHERE id=?", (rma_id,))
    return {"troca_id": troca_id, "diferenca": diferenca,
            "credito_ou_estorno": "credito" if diferenca < 0 else "estorno"}


def listar(status: str | None = None) -> list[dict]:
    sql = (
        "SELECT r.*, p.sku, p.nome AS produto_nome, o.numero AS venda, o.cliente"
        " FROM rma r JOIN produtos_cadastro p ON p.id=r.produto_id"
        " JOIN orcamentos o ON o.id=r.orcamento_id"
    )
    args: list = []
    if status:
        sql += " WHERE r.status=?"
        args.append(status)
    sql += " ORDER BY r.id DESC LIMIT 200"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def credito_cliente(cliente_id: int) -> dict:
    with system_conn() as conn:
        itens = [dict(r) for r in conn.execute(
            "SELECT * FROM credito_cliente WHERE cliente_id=? AND status='aberto' ORDER BY id DESC",
            (cliente_id,),
        ).fetchall()]
        saldo = conn.execute(
            "SELECT COALESCE(SUM(saldo),0) AS total FROM credito_cliente WHERE cliente_id=? AND status='aberto'",
            (cliente_id,),
        ).fetchone()
    return {"cliente_id": cliente_id, "saldo": float(saldo["total"] or 0), "creditos": itens}