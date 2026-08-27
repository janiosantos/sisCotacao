from __future__ import annotations

from catalog_server.db import next_cotacao_numero, system_conn


class QuoteRepository:

    # ------------------------------------------------------------------

    def create(
        self,
        titulo: str,
        cliente: str,
        observacoes: str,
        fornecedor_ids: list[int],
        itens: list[dict],
    ) -> tuple[int, str]:
        """Cria a cotação. Cada item: `{"produto_id": int, "quantidade": float,
        "descricao": str}` — itens livres (tamanho/cor fora do cadastro) já
        chegam com `produto_id` resolvido pela API (variação criada sob o pai)."""
        with system_conn() as conn:
            numero = next_cotacao_numero(conn)
            cur = conn.execute(
                "INSERT INTO cotacoes (numero, titulo, cliente, observacoes) VALUES (?,?,?,?)",
                (numero, titulo or None, cliente or None, observacoes or None),
            )
            cotacao_id = cur.lastrowid
            for it in itens:
                conn.execute(
                    "INSERT OR IGNORE INTO cotacao_itens (cotacao_id, produto_id, descricao, quantidade) VALUES (?,?,?,?)",
                    (
                        cotacao_id,
                        int(it["produto_id"]),
                        it.get("descricao") or "",
                        float(it.get("quantidade", 1) or 1),
                    ),
                )
            for fid in fornecedor_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO cotacao_fornecedores (cotacao_id, fornecedor_id) VALUES (?,?)",
                    (cotacao_id, fid),
                )
            return cotacao_id, numero

    # ------------------------------------------------------------------

    def list(self, status: str = "") -> list[dict]:
        sql = """
            SELECT c.*,
              (SELECT COUNT(*) FROM cotacao_itens ci WHERE ci.cotacao_id = c.id) AS n_itens,
              (SELECT COUNT(*) FROM cotacao_fornecedores cf WHERE cf.cotacao_id = c.id) AS n_fornecedores,
              (SELECT COUNT(*) FROM cotacao_fornecedores cf WHERE cf.cotacao_id = c.id AND cf.status='respondido') AS n_respostas
            FROM cotacoes c
        """
        params: list = []
        if status:
            sql += " WHERE c.status = ?"
            params.append(status)
        sql += " ORDER BY c.id DESC"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    # ------------------------------------------------------------------

    def get(self, cotacao_id: int) -> dict | None:
        with system_conn() as conn:
            cotacao = conn.execute(
                "SELECT * FROM cotacoes WHERE id=?", (cotacao_id,)
            ).fetchone()
            if cotacao is None:
                return None
            itens = conn.execute(
                "SELECT id, produto_id, descricao, quantidade FROM cotacao_itens WHERE cotacao_id=? ORDER BY id",
                (cotacao_id,),
            ).fetchall()
            fornecedores = conn.execute(
                """SELECT cf.fornecedor_id, cf.status, f.nome, f.whatsapp, f.email
                   FROM cotacao_fornecedores cf JOIN fornecedores f ON f.id = cf.fornecedor_id
                   WHERE cf.cotacao_id = ?
                   ORDER BY f.nome""",
                (cotacao_id,),
            ).fetchall()
            precos = conn.execute(
                """SELECT cp.*, fv.unidade_compra, fv.fator_conversao
                   FROM cotacao_precos cp
                   JOIN cotacao_itens ci ON ci.id = cp.cotacao_item_id
                   LEFT JOIN fornecedor_variantes fv
                           ON fv.fornecedor_id = cp.fornecedor_id AND fv.produto_id = ci.produto_id
                   WHERE ci.cotacao_id = ?""",
                (cotacao_id,),
            ).fetchall()
            vencedores = conn.execute(
                "SELECT * FROM pedido_itens WHERE cotacao_id = ?",
                (cotacao_id,),
            ).fetchall()
            return {
                "cotacao": dict(cotacao),
                "itens": [dict(r) for r in itens],
                "fornecedores": [dict(r) for r in fornecedores],
                "precos": [dict(r) for r in precos],
                "vencedores": [dict(r) for r in vencedores],
            }

    # ------------------------------------------------------------------

    def update_fields(self, cotacao_id: int, titulo: str, cliente: str, observacoes: str, status: str) -> None:
        fields, params = [], []
        for key, value in (("titulo", titulo), ("cliente", cliente), ("observacoes", observacoes), ("status", status)):
            if value is not None:
                fields.append(f"{key}=?")
                params.append(value)
        if not fields:
            return
        params.append(cotacao_id)
        with system_conn() as conn:
            conn.execute(f"UPDATE cotacoes SET {', '.join(fields)} WHERE id=?", params)

    # ------------------------------------------------------------------

    def add_fornecedor(self, cotacao_id: int, fornecedor_id: int) -> None:
        with system_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO cotacao_fornecedores (cotacao_id, fornecedor_id) VALUES (?,?)",
                (cotacao_id, fornecedor_id),
            )

    # ------------------------------------------------------------------

    def remove_fornecedor(self, cotacao_id: int, fornecedor_id: int) -> None:
        with system_conn() as conn:
            conn.execute(
                "DELETE FROM cotacao_fornecedores WHERE cotacao_id=? AND fornecedor_id=?",
                (cotacao_id, fornecedor_id),
            )
            conn.execute(
                """DELETE FROM cotacao_precos WHERE fornecedor_id=? AND cotacao_item_id IN
                   (SELECT id FROM cotacao_itens WHERE cotacao_id=?)""",
                (fornecedor_id, cotacao_id),
            )

    # ------------------------------------------------------------------

    def add_item(self, cotacao_id: int, produto_id: int, quantidade: float, descricao: str = "") -> None:
        with system_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO cotacao_itens (cotacao_id, produto_id, descricao, quantidade) VALUES (?,?,?,?)",
                (cotacao_id, produto_id, descricao or "", quantidade),
            )

    # ------------------------------------------------------------------

    def update_item(self, cotacao_id: int, item_id: int, quantidade: float) -> None:
        with system_conn() as conn:
            conn.execute(
                "UPDATE cotacao_itens SET quantidade=? WHERE id=? AND cotacao_id=?",
                (quantidade, item_id, cotacao_id),
            )

    # ------------------------------------------------------------------

    def remove_item(self, cotacao_id: int, item_id: int) -> None:
        with system_conn() as conn:
            conn.execute("DELETE FROM cotacao_itens WHERE id=? AND cotacao_id=?", (item_id, cotacao_id))

    # ------------------------------------------------------------------

    def item_por_produto(self, cotacao_id: int, produto_id: int) -> int | None:
        """Devolve o cotacao_item_id de um produto dentro da cotação (o microserviço
        devolve produto_id = id de variante do catálogo, que é o usado no cadastro)."""
        with system_conn() as conn:
            row = conn.execute(
                "SELECT id FROM cotacao_itens WHERE cotacao_id=? AND produto_id=? ORDER BY id ASC LIMIT 1",
                (cotacao_id, produto_id),
            ).fetchone()
        return row["id"] if row else None

    # ------------------------------------------------------------------

    def registrar_preco(
        self,
        cotacao_id: int,
        cotacao_item_id: int,
        fornecedor_id: int,
        preco_unitario: float,
        prazo_entrega_dias: int | None,
        observacao: str,
        validade_preco_em: str | None = None,
    ) -> None:
        with system_conn() as conn:
            conn.execute(
                """INSERT INTO cotacao_precos
                     (cotacao_item_id, fornecedor_id, preco_unitario, prazo_entrega_dias,
                      observacao, registrado_em, validade_preco_em)
                   VALUES (?,?,?,?,?, datetime('now'), ?)
                   ON CONFLICT(cotacao_item_id, fornecedor_id) DO UPDATE SET
                     preco_unitario=excluded.preco_unitario,
                     prazo_entrega_dias=excluded.prazo_entrega_dias,
                     observacao=excluded.observacao,
                     validade_preco_em=excluded.validade_preco_em,
                     registrado_em=datetime('now')""",
                (
                    cotacao_item_id,
                    fornecedor_id,
                    preco_unitario,
                    prazo_entrega_dias,
                    observacao or None,
                    validade_preco_em or None,
                ),
            )
            conn.execute(
                "UPDATE cotacao_fornecedores SET status='respondido' WHERE cotacao_id=? AND fornecedor_id=?",
                (cotacao_id, fornecedor_id),
            )

    # ------------------------------------------------------------------

    def fechar(self, cotacao_id: int, escolhas: list[dict]) -> None:
        with system_conn() as conn:
            conn.execute("DELETE FROM pedido_itens WHERE cotacao_id=?", (cotacao_id,))
            for v in escolhas:
                conn.execute(
                    """INSERT INTO pedido_itens
                         (cotacao_id, cotacao_item_id, fornecedor_id, preco_unitario, quantidade)
                       VALUES (?,?,?,?,?)""",
                    (cotacao_id, v["cotacao_item_id"], v["fornecedor_id"], v["preco_unitario"], v["quantidade"]),
                )
            conn.execute(
                "UPDATE cotacoes SET status='fechada', fechado_em=datetime('now') WHERE id=?",
                (cotacao_id,),
            )

    # ------------------------------------------------------------------

    def reabrir(self, cotacao_id: int) -> None:
        with system_conn() as conn:
            conn.execute("UPDATE cotacoes SET status='aberta', fechado_em=NULL WHERE id=?", (cotacao_id,))

    # ------------------------------------------------------------------

    def set_status(self, cotacao_id: int, status: str) -> None:
        with system_conn() as conn:
            conn.execute("UPDATE cotacoes SET status=? WHERE id=?", (status, cotacao_id))

    # ------------------------------------------------------------------

    def historico_precos(self, produto_id: int) -> list[dict]:
        with system_conn() as conn:
            rows = conn.execute(
                """SELECT cp.preco_unitario, cp.prazo_entrega_dias, cp.registrado_em,
                          cp.validade_preco_em,
                          f.id AS fornecedor_id, f.nome AS fornecedor_nome,
                          c.numero AS cotacao_numero, c.id AS cotacao_id
                   FROM cotacao_precos cp
                   JOIN cotacao_itens ci ON ci.id = cp.cotacao_item_id
                   JOIN fornecedores f ON f.id = cp.fornecedor_id
                   JOIN cotacoes c ON c.id = ci.cotacao_id
                   WHERE ci.produto_id = ?
                   ORDER BY cp.registrado_em ASC""",
                (produto_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------

    def produtos_com_historico(self) -> list[dict]:
        with system_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT produto_id FROM cotacao_precos cp JOIN cotacao_itens ci ON ci.id = cp.cotacao_item_id"
            ).fetchall()
        return [r["produto_id"] for r in rows]
