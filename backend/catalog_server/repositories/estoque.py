from __future__ import annotations

from catalog_server.db import system_conn


class EstoqueRepository:

    def saldo(
        self,
        deposito_id: int | None = None,
        variante_id: int | None = None,
        termo: str | None = None,
        familia_id: int | None = None,
    ) -> list[dict]:
        sql = (
            "SELECT s.id, s.deposito_id, s.variante_id, s.quantidade, s.reserva,"
            " s.atualizado_em, d.nome AS deposito_nome,"
            " v.sku, v.preco, p.nome AS produto_nome, p.marca,"
            " p.familia_id, f.nome AS familia_nome,"
            " v.unidade_venda, v.embalagem, v.fator_conversao, v.ncm,"
            " v.unidade_tributavel, v.localizacao,"
            " s.estoque_minimo, s.estoque_maximo,"
            " CASE WHEN s.estoque_minimo > 0 AND s.quantidade < s.estoque_minimo THEN 'ruptura'"
            "  WHEN s.estoque_maximo > 0 AND s.quantidade > s.estoque_maximo THEN 'excesso'"
            "  ELSE 'ok' END AS situacao"
            " FROM estoque_saldo s"
            " JOIN depositos d ON d.id = s.deposito_id"
            " JOIN variantes v ON v.id = s.variante_id"
            " JOIN produtos_cadastro p ON p.id = v.produto_id"
            " LEFT JOIN familias f ON f.id = p.familia_id"
        )
        where: list[str] = []
        args: list = []
        if deposito_id is not None:
            where.append("s.deposito_id = ?")
            args.append(deposito_id)
        if variante_id is not None:
            where.append("s.variante_id = ?")
            args.append(variante_id)
        if familia_id is not None:
            where.append("p.familia_id = ?")
            args.append(familia_id)
        if termo:
            where.append("(p.nome LIKE ? OR v.sku LIKE ? OR p.marca LIKE ?)")
            like = f"%{termo}%"
            args.extend([like, like, like])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY p.nome, v.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def movimentar(
        self,
        deposito_id: int,
        variante_id: int,
        tipo: str,
        quantidade: float,
        documento: str | None = None,
        observacao: str | None = None,
        lote_id: int | None = None,
        usuario_id: int | None = None,
        _conn=None,
    ) -> dict:
        ctx = system_conn() if _conn is None else None
        conn = _conn or ctx.__enter__()
        try:
            saldo_row = conn.execute(
                "SELECT id, quantidade FROM estoque_saldo WHERE deposito_id=? AND variante_id=?",
                (deposito_id, variante_id),
            ).fetchone()
            if saldo_row:
                saldo_atual = float(saldo_row["quantidade"] or 0)
                saldo_id = saldo_row["id"]
            else:
                saldo_atual = 0.0
                conn.execute(
                    "INSERT INTO estoque_saldo (deposito_id, variante_id, quantidade, reserva)"
                    " VALUES (?,?,0,0)",
                    (deposito_id, variante_id),
                )
                saldo_id = conn.execute(
                    "SELECT id FROM estoque_saldo WHERE deposito_id=? AND variante_id=?",
                    (deposito_id, variante_id),
                ).fetchone()["id"]

            if tipo in ("entrada", "inventario"):
                novo_saldo = saldo_atual + quantidade
            elif tipo == "saida":
                novo_saldo = max(0, saldo_atual - quantidade)
            elif tipo == "ajuste":
                novo_saldo = max(0, quantidade)
            elif tipo == "transferencia":
                novo_saldo = max(0, saldo_atual - quantidade)
            else:
                novo_saldo = saldo_atual

            conn.execute(
                "UPDATE estoque_saldo SET quantidade=?, atualizado_em=datetime('now') WHERE id=?",
                (novo_saldo, saldo_id),
            )

            cur = conn.execute(
                "INSERT INTO estoque_movimento (deposito_id, variante_id, tipo, quantidade,"
                " saldo_anterior, saldo_posterior, documento, observacao, lote_id, usuario_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    deposito_id,
                    variante_id,
                    tipo,
                    quantidade,
                    saldo_atual,
                    novo_saldo,
                    documento,
                    observacao,
                    lote_id,
                    usuario_id,
                ),
            )

            return {
                "movimento_id": cur.lastrowid,
                "saldo_anterior": saldo_atual,
                "saldo_posterior": novo_saldo,
            }
        finally:
            if ctx:
                ctx.__exit__(None, None, None)

    def movimentos(
        self,
        deposito_id: int | None = None,
        variante_id: int | None = None,
        tipo: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        sql = (
            "SELECT m.*, d.nome AS deposito_nome,"
            " v.sku, p.nome AS produto_nome, p.marca"
            " FROM estoque_movimento m"
            " JOIN depositos d ON d.id = m.deposito_id"
            " JOIN variantes v ON v.id = m.variante_id"
            " JOIN produtos_cadastro p ON p.id = v.produto_id"
        )
        where: list[str] = []
        args: list = []
        if deposito_id is not None:
            where.append("m.deposito_id = ?")
            args.append(deposito_id)
        if variante_id is not None:
            where.append("m.variante_id = ?")
            args.append(variante_id)
        if tipo:
            where.append("m.tipo = ?")
            args.append(tipo)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def transferir(
        self,
        origem_id: int,
        destino_id: int,
        variante_id: int,
        quantidade: float,
        observacao: str | None = None,
        usuario_id: int | None = None,
    ) -> dict:
        with system_conn() as conn:
            self.movimentar(origem_id, variante_id, "transferencia", quantidade, "Transferência", observacao, None, usuario_id, _conn=conn)
            self.movimentar(destino_id, variante_id, "entrada", quantidade, "Transferência", observacao, None, usuario_id, _conn=conn)
        return {"ok": True}


class LoteRepository:

    def list(self, deposito_id: int | None = None, variante_id: int | None = None) -> list[dict]:
        sql = (
            "SELECT l.*, d.nome AS deposito_nome,"
            " v.sku, p.nome AS produto_nome, p.marca"
            " FROM lotes l"
            " JOIN depositos d ON d.id = l.deposito_id"
            " JOIN variantes v ON v.id = l.variante_id"
            " JOIN produtos_cadastro p ON p.id = v.produto_id"
        )
        where: list[str] = []
        args: list = []
        if deposito_id is not None:
            where.append("l.deposito_id = ?")
            args.append(deposito_id)
        if variante_id is not None:
            where.append("l.variante_id = ?")
            args.append(variante_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY l.data_validade, l.codigo"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, lote_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM lotes WHERE id=?", (lote_id,)).fetchone()
            return dict(row) if row else None

    def create(
        self,
        deposito_id: int,
        variante_id: int,
        codigo: str,
        quantidade: float = 0,
        data_fabricacao: str | None = None,
        data_validade: str | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO lotes (deposito_id, variante_id, codigo, quantidade, data_fabricacao, data_validade)"
                " VALUES (?,?,?,?,?,?)",
                (deposito_id, variante_id, codigo.strip(), quantidade, data_fabricacao, data_validade),
            )
            return cur.lastrowid


estoque_repo = EstoqueRepository()
lote_repo = LoteRepository()
