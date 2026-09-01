"""Conferência de três vias (REC-003): compara pedido × recebimento × NF/XML,
aplica tolerâncias por fornecedor e só libera efeitos definitivos após aprovação
quando há divergência.
"""

from __future__ import annotations

from catalog_server.db import system_conn


def _pedido_linhas(conn, pedido_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT pi.preco_unitario, ci.produto_id, ci.quantidade AS qtd_pedido"
        " FROM pedido_itens pi JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id"
        " WHERE pi.pedido_id=?",
        (pedido_id,),
    ).fetchall()]


def _tolerancias(conn, fornecedor_id: int) -> dict:
    row = conn.execute(
        "SELECT tolerancia_preco_pct, tolerancia_qtd_pct, exige_aprovacao FROM tolerancias_compra WHERE fornecedor_id=?",
        (fornecedor_id,),
    ).fetchone()
    if not row:
        return {"preco_pct": 10.0, "qtd_pct": 10.0, "exige_aprovacao": True}
    return {"preco_pct": float(row["tolerancia_preco_pct"] or 0), "qtd_pct": float(row["tolerancia_qtd_pct"] or 0),
            "exige_aprovacao": bool(row["exige_aprovacao"])}


def conferir(recebimento_id: int, itens_nf: list[dict]) -> dict:
    """Compara as linhas da NF com o pedido, grava divergências e define o status."""
    with system_conn() as conn:
        rec = conn.execute("SELECT * FROM recebimento WHERE id=?", (recebimento_id,)).fetchone()
        if not rec:
            raise LookupError("Recebimento não encontrado")
        pedido_linhas = {r["produto_id"]: r for r in _pedido_linhas(conn, rec["pedido_id"])}
        tol = _tolerancias(conn, rec["fornecedor_id"])
        nf = {int(n["produto_id"]): n for n in itens_nf if n.get("produto_id")}

        divergentes = 0
        for produto_id, n in nf.items():
            qtd_nf = float(n.get("quantidade") or 0)
            preco_nf = float(n.get("preco_unitario") or 0)
            p = pedido_linhas.get(produto_id)
            if not p:
                # item da NF sem pedido → divergência fiscal/quantidade
                conn.execute(
                    "INSERT INTO recebimento_divergencia (recebimento_id, produto_id, qtd_pedido, qtd_nf,"
                    " preco_pedido, preco_nf, tipo, dif_pct, dentro_tolerancia)"
                    " VALUES (?,?,0,?,NULL,?,'quantidade',100.0,FALSE)"
                    " ON CONFLICT (recebimento_id, produto_id, tipo) DO UPDATE SET qtd_nf=EXCLUDED.qtd_nf,"
                    " preco_nf=EXCLUDED.preco_nf, dif_pct=100.0, dentro_tolerancia=FALSE",
                    (recebimento_id, produto_id, qtd_nf, preco_nf),
                )
                divergentes += 1
                continue
            qtd_pedido = float(p["qtd_pedido"] or 0)
            preco_pedido = float(p["preco_unitario"] or 0)
            dif_qtd = _pct(qtd_nf, qtd_pedido)
            dif_preco = _pct(preco_nf, preco_pedido)
            dentro_qtd = abs(dif_qtd) <= tol["qtd_pct"]
            dentro_preco = abs(dif_preco) <= tol["preco_pct"]
            conn.execute(
                "INSERT INTO recebimento_divergencia (recebimento_id, produto_id, qtd_pedido, qtd_nf,"
                " preco_pedido, preco_nf, tipo, dif_pct, dentro_tolerancia)"
                " VALUES (?,?,?,?,?,?,'quantidade',?,?)"
                " ON CONFLICT (recebimento_id, produto_id, tipo) DO UPDATE SET qtd_pedido=EXCLUDED.qtd_pedido,"
                " qtd_nf=EXCLUDED.qtd_nf, dif_pct=EXCLUDED.dif_pct, dentro_tolerancia=EXCLUDED.dentro_tolerancia",
                (recebimento_id, produto_id, qtd_pedido, qtd_nf, preco_pedido, preco_nf, dif_qtd, dentro_qtd),
            )
            conn.execute(
                "INSERT INTO recebimento_divergencia (recebimento_id, produto_id, qtd_pedido, qtd_nf,"
                " preco_pedido, preco_nf, tipo, dif_pct, dentro_tolerancia)"
                " VALUES (?,?,?,?,?,?,'preco',?,?)"
                " ON CONFLICT (recebimento_id, produto_id, tipo) DO UPDATE SET preco_pedido=EXCLUDED.preco_pedido,"
                " preco_nf=EXCLUDED.preco_nf, dif_pct=EXCLUDED.dif_pct, dentro_tolerancia=EXCLUDED.dentro_tolerancia",
                (recebimento_id, produto_id, qtd_pedido, qtd_nf, preco_pedido, preco_nf, dif_preco, dentro_preco),
            )
            if not dentro_qtd or not dentro_preco:
                divergentes += 1

        status = "divergente" if divergentes > 0 else "aprovado"
        conn.execute("UPDATE recebimento SET status_tres_vias=? WHERE id=?", (status, recebimento_id))
    return {"status_tres_vias": status, "divergencias": divergentes, "tolerancias": tol}


def _pct(novo: float, base: float) -> float:
    if base in (0, None):
        return 0.0
    return round((novo - base) / base * 100.0, 4)


def aprovar(recebimento_id: int, usuario_id: int | None = None) -> dict:
    with system_conn() as conn:
        rec = conn.execute("SELECT status_tres_vias FROM recebimento WHERE id=?", (recebimento_id,)).fetchone()
        if not rec:
            raise LookupError("Recebimento não encontrado")
        if rec["status_tres_vias"] == "rejeitado":
            raise ValueError("Recebimento rejeitado não pode ser aprovado")
        conn.execute(
            "UPDATE recebimento SET status_tres_vias='aprovado', divergencia_aprovada_por=?, divergencia_aprovada_em=NOW()"
            " WHERE id=?",
            (usuario_id, recebimento_id),
        )
        conn.execute("UPDATE recebimento_divergencia SET aprovada=TRUE WHERE recebimento_id=?", (recebimento_id,))
    return {"recebimento_id": recebimento_id, "status_tres_vias": "aprovado"}


def rejeitar(recebimento_id: int, motivo: str) -> dict:
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("motivo é obrigatório")
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE recebimento SET status_tres_vias='rejeitado', divergencia_rejeitada_motivo=? WHERE id=?",
            (motivo, recebimento_id),
        )
        if cur.rowcount == 0:
            raise LookupError("Recebimento não encontrado")
    return {"recebimento_id": recebimento_id, "status_tres_vias": "rejeitado"}


def divergencias(recebimento_id: int) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT d.*, p.sku, p.nome AS produto_nome"
            " FROM recebimento_divergencia d JOIN produtos_cadastro p ON p.id=d.produto_id"
            " WHERE d.recebimento_id=? ORDER BY d.id",
            (recebimento_id,),
        ).fetchall()]


def status(recebimento_id: int) -> str:
    with system_conn() as conn:
        row = conn.execute("SELECT status_tres_vias FROM recebimento WHERE id=?", (recebimento_id,)).fetchone()
    return row["status_tres_vias"] if row else "nao_encontrado"