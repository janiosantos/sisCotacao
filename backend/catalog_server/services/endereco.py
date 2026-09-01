"""Endereçamento (EST-007): posições de armazenagem (rua-módulo-posição-nível),
saldo por posição, posição primária e movimentação entre endereços (logada).
"""

from __future__ import annotations

from catalog_server.db import system_conn


def listar_posicoes(deposito_id: int, busca: str | None = None) -> list[dict]:
    sql = (
        "SELECT p.id, p.deposito_id, p.codigo, p.ativo, p.criado_em, d.nome AS deposito_nome,"
        " (SELECT COUNT(*) FROM endereco_estoque e WHERE e.posicao_id=p.id AND e.quantidade<>0) AS posicoes_ocupadas"
        " FROM endereco_posicao p JOIN depositos d ON d.id=p.deposito_id"
    )
    args: list = []
    where: list[str] = []
    if deposito_id:
        where.append("p.deposito_id=?")
        args.append(deposito_id)
    if busca:
        where.append("p.codigo ILIKE ?")
        args.append(f"%{busca}%")
    where.append("p.ativo")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY p.codigo"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def criar_posicao(deposito_id: int, codigo: str) -> dict:
    codigo = (codigo or "").strip().upper()
    if not codigo:
        raise ValueError("código da posição é obrigatório")
    with system_conn() as conn:
        try:
            pos_id = conn.execute(
                "INSERT INTO endereco_posicao (deposito_id, codigo) VALUES (?,?) RETURNING id",
                (deposito_id, codigo),
            ).fetchone()["id"]
        except Exception as exc:
            if "uq_endereco_codigo" in str(exc) or "duplicate" in str(exc).lower():
                raise ValueError("Já existe posição com este código no depósito")
            raise
        row = conn.execute(
            "SELECT p.*, d.nome AS deposito_nome FROM endereco_posicao p"
            " JOIN depositos d ON d.id=p.deposito_id WHERE p.id=?",
            (pos_id,),
        ).fetchone()
        return dict(row)


def excluir_posicao(posicao_id: int) -> bool:
    with system_conn() as conn:
        ocupado = conn.execute(
            "SELECT 1 FROM endereco_estoque WHERE posicao_id=? AND quantidade<>0",
            (posicao_id,),
        ).fetchone()
        if ocupado:
            raise ValueError("Posição com itens não pode ser excluída")
        cur = conn.execute(
            "UPDATE endereco_posicao SET ativo=FALSE WHERE id=? AND ativo",
            (posicao_id,),
        )
        return cur.rowcount > 0


def estoque_na_posicao(posicao_id: int) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT e.posicao_id, e.produto_id, e.quantidade, e.primaria,"
            " p.sku, p.nome AS produto_nome, p.unidade_venda"
            " FROM endereco_estoque e JOIN produtos_cadastro p ON p.id=e.produto_id"
            " WHERE e.posicao_id=? AND e.quantidade<>0 ORDER BY p.nome",
            (posicao_id,),
        ).fetchall()]


def posicao_primaria(produto_id: int, deposito_id: int) -> dict | None:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT e.posicao_id, e.produto_id, e.quantidade, p.codigo"
            " FROM endereco_estoque e"
            " JOIN endereco_posicao p ON p.id=e.posicao_id"
            " WHERE e.produto_id=? AND p.deposito_id=? AND e.primaria AND e.quantidade<>0"
            " ORDER BY e.quantidade DESC LIMIT 1",
            (produto_id, deposito_id),
        ).fetchone()
    return dict(row) if row else None


def _mov_log(conn, posicao_id, produto_id, tipo, quantidade, usuario_id) -> None:
    conn.execute(
        "INSERT INTO endereco_movimento (posicao_id, produto_id, tipo, quantidade, usuario_id)"
        " VALUES (?,?,?,?,?)",
        (posicao_id, produto_id, tipo, quantidade, usuario_id),
    )


def _mudar_quantidade(conn, posicao_id, produto_id, delta) -> None:
    conn.execute(
        "INSERT INTO endereco_estoque (posicao_id, produto_id, quantidade)"
        " VALUES (?,?,?) ON CONFLICT (posicao_id, produto_id)"
        " DO UPDATE SET quantidade = endereco_estoque.quantidade + EXCLUDED.quantidade",
        (posicao_id, produto_id, delta),
    )
    conn.execute(
        "DELETE FROM endereco_estoque WHERE posicao_id=? AND produto_id=? AND quantidade=0",
        (posicao_id, produto_id),
    )


def movimentar(
    de_posicao_id: int | None,
    para_posicao_id: int | None,
    produto_id: int,
    quantidade: float,
    usuario_id: int | None = None,
    marcar_primaria: bool = True,
) -> dict:
    """Move quantidade entre posições. `de=None` ⇒ entrada (colocação inicial);
    `para=None` ⇒ saída (retirada). Registra `endereco_movimento`."""
    q = float(quantidade)
    if q <= 0:
        raise ValueError("Quantidade deve ser positiva")
    if de_posicao_id is None and para_posicao_id is None:
        raise ValueError("Informe posição de origem ou destino")
    with system_conn() as conn:
        if de_posicao_id is not None:
            atual = conn.execute(
                "SELECT quantidade FROM endereco_estoque WHERE posicao_id=? AND produto_id=?",
                (de_posicao_id, produto_id),
            ).fetchone()
            disp = float(atual["quantidade"] or 0) if atual else 0.0
            if q > disp:
                raise ValueError(f"Quantidade na posição de origem insuficiente: {disp:g}")
            _mudar_quantidade(conn, de_posicao_id, produto_id, -q)
            _mov_log(conn, de_posicao_id, produto_id, "movimentacao", -q, usuario_id)
        if para_posicao_id is not None:
            _mudar_quantidade(conn, para_posicao_id, produto_id, q)
            _mov_log(conn, para_posicao_id, produto_id, "entrada" if de_posicao_id is None else "movimentacao", q, usuario_id)
            if marcar_primaria:
                # primeira colocação do produto no depósito vira posição primária
                pos_row = conn.execute(
                    "SELECT deposito_id FROM endereco_posicao WHERE id=?",
                    (para_posicao_id,),
                ).fetchone()
                if pos_row:
                    existe_primaria = conn.execute(
                        "SELECT 1 FROM endereco_estoque e JOIN endereco_posicao p ON p.id=e.posicao_id"
                        " WHERE e.produto_id=? AND p.deposito_id=? AND e.primaria AND e.quantidade<>0",
                        (produto_id, pos_row["deposito_id"]),
                    ).fetchone()
                    if not existe_primaria:
                        conn.execute(
                            "UPDATE endereco_estoque SET primaria=TRUE WHERE posicao_id=? AND produto_id=?",
                            (para_posicao_id, produto_id),
                        )
    return {"de_posicao_id": de_posicao_id, "para_posicao_id": para_posicao_id,
            "produto_id": produto_id, "quantidade": q}


def ultimos_movimentos(limit: int = 20) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT m.*, p.codigo, pr.sku, pr.nome AS produto_nome, u.nome AS usuario_nome"
            " FROM endereco_movimento m"
            " JOIN endereco_posicao p ON p.id=m.posicao_id"
            " JOIN produtos_cadastro pr ON pr.id=m.produto_id"
            " LEFT JOIN usuarios u ON u.id=m.usuario_id"
            " ORDER BY m.id DESC LIMIT ?",
            (limit,),
        ).fetchall()]