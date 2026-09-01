"""Inventário cíclico (EST-006): ciclo de contagem, lista de contagem, registro
da contagem, comparação com o saldo e ajuste aprovado via fato 'inventario'.

Ajuste só ocorre após aprovação do ciclo. A diferença é explicável pelo ledger.
"""

from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo


def criar_ciclo(deposito_id: int, nome: str, usuario_id: int | None = None) -> dict:
    """Cria o ciclo e gera a lista de contagem (produtos com saldo <> 0 no depósito)."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("nome do ciclo é obrigatório")
    with system_conn() as conn:
        ciclo_id = conn.execute(
            "INSERT INTO inventario_ciclo (deposito_id, nome, status, criado_por)"
            " VALUES (?,?, 'planejado', ?) RETURNING id",
            (deposito_id, nome, usuario_id),
        ).fetchone()["id"]
        linhas = conn.execute(
            "SELECT produto_id, quantidade AS saldo_esperado FROM estoque_saldo"
            " WHERE deposito_id=? AND quantidade <> 0 ORDER BY produto_id",
            (deposito_id,),
        ).fetchall()
        for r in linhas:
            conn.execute(
                "INSERT INTO inventario_contagem (ciclo_id, produto_id, saldo_esperado)"
                " VALUES (?,?,?) ON CONFLICT (ciclo_id, produto_id) DO NOTHING",
                (ciclo_id, r["produto_id"], r["saldo_esperado"]),
            )
        conn.execute(
            "UPDATE inventario_ciclo SET status='em_andamento' WHERE id=?",
            (ciclo_id,),
        )
    return {
        "id": ciclo_id,
        "deposito_id": deposito_id,
        "nome": nome,
        "status": "em_andamento",
        "itens": len(linhas),
    }


def listar_ciclos(deposito_id: int | None = None) -> list[dict]:
    sql = (
        "SELECT c.id, c.deposito_id, c.nome, c.status, c.criado_por, c.criado_em,"
        " c.fechado_em, d.nome AS deposito_nome,"
        " COUNT(g.id) FILTER (WHERE g.status IN ('pendente')) AS pendentes,"
        " COUNT(g.id) FILTER (WHERE g.status IN ('conferido','ok','ajustado')) AS conferidas,"
        " COUNT(g.id) FILTER (WHERE g.status='divergente') AS divergentes"
        " FROM inventario_ciclo c"
        " JOIN depositos d ON d.id=c.deposito_id"
        " LEFT JOIN inventario_contagem g ON g.ciclo_id=c.id"
    )
    args: list = []
    if deposito_id:
        sql += " WHERE c.deposito_id=?"
        args.append(deposito_id)
    sql += " GROUP BY c.id, d.nome ORDER BY c.id DESC"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def detalhe_ciclo(ciclo_id: int) -> dict | None:
    with system_conn() as conn:
        ciclo = conn.execute(
            "SELECT c.*, d.nome AS deposito_nome FROM inventario_ciclo c"
            " JOIN depositos d ON d.id=c.deposito_id WHERE c.id=?",
            (ciclo_id,),
        ).fetchone()
        if not ciclo:
            return None
        contagens = conn.execute(
            "SELECT g.*, p.sku, p.nome AS produto_nome, p.unidade_venda,"
            " u.nome AS executor_nome"
            " FROM inventario_contagem g"
            " JOIN produtos_cadastro p ON p.id=g.produto_id"
            " LEFT JOIN usuarios u ON u.id=g.executor_id"
            " WHERE g.ciclo_id=? ORDER BY p.nome",
            (ciclo_id,),
        ).fetchall()
        itens = []
        for r in contagens:
            esperado = float(r["saldo_esperado"] or 0)
            contado = float(r["quantidade_contada"]) if r["quantidade_contada"] is not None else None
            d = dict(r)
            d["saldo_esperado"] = esperado
            d["quantidade_contada"] = contado
            d["diferenca"] = round(contado - esperado, 3) if contado is not None else None
            itens.append(d)
        out = dict(ciclo)
        out["contagens"] = itens
        return out


def registrar_contagem(
    ciclo_id: int,
    produto_id: int,
    quantidade_contada: float,
    executor_id: int | None = None,
    observacao: str | None = None,
) -> dict:
    with system_conn() as conn:
        ciclo = conn.execute(
            "SELECT status FROM inventario_ciclo WHERE id=?",
            (ciclo_id,),
        ).fetchone()
        if not ciclo:
            raise LookupError("Ciclo não encontrado")
        if ciclo["status"] in ("ajustado", "cancelado"):
            raise ValueError(f"Ciclo {ciclo['status']} não aceita contagens")
        row = conn.execute(
            "SELECT id, saldo_esperado FROM inventario_contagem"
            " WHERE ciclo_id=? AND produto_id=?",
            (ciclo_id, produto_id),
        ).fetchone()
        if not row:
            raise LookupError("Produto não está na lista de contagem do ciclo")
        q = float(quantidade_contada)
        esperado = float(row["saldo_esperado"] or 0)
        status = "conferido" if q == esperado else "divergente"
        conn.execute(
            "UPDATE inventario_contagem SET quantidade_contada=?, executor_id=?,"
            " contada_em=NOW(), status=?, observacao=? WHERE id=?",
            (q, executor_id, status, observacao, row["id"]),
        )
        return {"ciclo_id": ciclo_id, "produto_id": produto_id, "quantidade_contada": q,
                "saldo_esperado": esperado, "diferenca": round(q - esperado, 3), "status": status}


def aprovar_ciclo(ciclo_id: int, usuario_id: int | None = None) -> dict:
    """Aplica o ajuste aprovado: para cada contagem conferida/divergente, gera o
    fato 'inventario' que leva o saldo à quantidade contada (idempotente por contagem)."""
    with system_conn() as conn:
        ciclo = conn.execute(
            "SELECT status, deposito_id FROM inventario_ciclo WHERE id=?",
            (ciclo_id,),
        ).fetchone()
        if not ciclo:
            raise LookupError("Ciclo não encontrado")
        if ciclo["status"] == "ajustado":
            return {"ciclo_id": ciclo_id, "duplicado": True, "ajustes": 0}
        if ciclo["status"] not in ("planejado", "em_andamento"):
            raise ValueError(f"Ciclo {ciclo['status']} não pode ser aprovado")
        pendentes = conn.execute(
            "SELECT COUNT(*) FROM inventario_contagem WHERE ciclo_id=? AND status='pendente'",
            (ciclo_id,),
        ).fetchone()["count"]
        if pendentes:
            raise ValueError(f"Existem {pendentes} contagem(ns) pendente(s) no ciclo")
        contagens = conn.execute(
            "SELECT * FROM inventario_contagem WHERE ciclo_id=? AND quantidade_contada IS NOT NULL",
            (ciclo_id,),
        ).fetchall()
    deposito_id = int(ciclo["deposito_id"])

    # Ajuste fora da transação de leitura (cada fato tem sua própria transação).
    ajustes = 0
    for g in contagens:
        esperado = float(g["saldo_esperado"] or 0)
        contado = float(g["quantidade_contada"])
        if contado != esperado:
            with system_conn() as conn2:
                conn2.execute(
                    "UPDATE inventario_contagem SET aprovado_por=?, aprovado_em=NOW(), status='ajustado'"
                    " WHERE id=?",
                    (usuario_id, g["id"]),
                )
                conn2.commit()
            estoque_repo.lancar_inventario(
                deposito_id,
                g["produto_id"],
                contado,
                justificativa=f"inventário cíclico #{ciclo_id}",
                idempotency_key=f"ciclo-{ciclo_id}-contagem-{g['id']}",
                usuario_id=usuario_id,
            )
            ajustes += 1
        else:
            with system_conn() as conn2:
                conn2.execute(
                    "UPDATE inventario_contagem SET aprovado_por=?, aprovado_em=NOW(), status='ok'"
                    " WHERE id=?",
                    (usuario_id, g["id"]),
                )
                conn2.commit()
    with system_conn() as conn:
        conn.execute(
            "UPDATE inventario_ciclo SET status='ajustado', fechado_em=NOW() WHERE id=?",
            (ciclo_id,),
        )
    return {"ciclo_id": ciclo_id, "duplicado": False, "ajustes": ajustes}


def cancelar_ciclo(ciclo_id: int) -> bool:
    with system_conn() as conn:
        ciclo = conn.execute(
            "SELECT status FROM inventario_ciclo WHERE id=?",
            (ciclo_id,),
        ).fetchone()
        if not ciclo or ciclo["status"] in ("ajustado", "cancelado"):
            return False
        conn.execute(
            "UPDATE inventario_ciclo SET status='cancelado', fechado_em=NOW() WHERE id=?",
            (ciclo_id,),
        )
        return True