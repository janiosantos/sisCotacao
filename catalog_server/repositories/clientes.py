from __future__ import annotations

from catalog_server.db import system_conn


class ClienteRepository:

    def list(self, somente_ativos: bool = False, vendedor_id: int | None = None) -> list[dict]:
        sql = (
            "SELECT c.*, v.nome AS vendedor_nome FROM clientes c"
            " LEFT JOIN vendedores v ON v.id = c.vendedor_id"
        )
        where: list[str] = []
        args: list = []
        if somente_ativos:
            where.append("c.ativo = 1")
        if vendedor_id is not None:
            where.append("c.vendedor_id = ?")
            args.append(vendedor_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY c.nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    # ------------------------------------------------------------------

    def buscar(self, termo: str, limite: int = 10) -> list[dict]:
        termo = (termo or "").strip()
        if not termo:
            return []
        like = f"%{termo}%"
        sql = (
            "SELECT c.*, v.nome AS vendedor_nome FROM clientes c"
            " LEFT JOIN vendedores v ON v.id = c.vendedor_id"
            " WHERE c.ativo = 1 AND ("
            "  c.nome LIKE ? COLLATE NOCASE OR c.doc LIKE ?"
            "  OR c.email LIKE ? OR c.telefone LIKE ? OR c.whatsapp LIKE ?"
            "  OR c.endereco LIKE ? OR c.cidade LIKE ? OR c.uf LIKE ?"
            " )"
            " ORDER BY c.nome LIMIT ?"
        )
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, (like, like, like, like, like, like, like, like, limite)).fetchall()]

    # ------------------------------------------------------------------

    def get(self, cliente_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM clientes WHERE id = ?", (cliente_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------

    def create(self, dados: dict) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO clientes (nome, tipo_pessoa, doc, email, telefone,"
                " whatsapp, endereco, cidade, uf, cep, vendedor_id, limite_credito,"
                " observacoes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    dados["nome"],
                    dados.get("tipo_pessoa", "f"),
                    dados.get("doc") or None,
                    dados.get("email") or None,
                    dados.get("telefone") or None,
                    dados.get("whatsapp") or None,
                    dados.get("endereco") or None,
                    dados.get("cidade") or None,
                    dados.get("uf") or None,
                    dados.get("cep") or None,
                    dados.get("vendedor_id") or None,
                    float(dados.get("limite_credito") or 0),
                    dados.get("observacoes") or None,
                ),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(self, cliente_id: int, dados: dict) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE clientes SET nome=?, tipo_pessoa=?, doc=?, email=?,"
                " telefone=?, whatsapp=?, endereco=?, cidade=?, uf=?, cep=?,"
                " vendedor_id=?, limite_credito=?, observacoes=?, atualizado_em="
                " datetime('now') WHERE id=?",
                (
                    dados["nome"],
                    dados.get("tipo_pessoa", "f"),
                    dados.get("doc") or None,
                    dados.get("email") or None,
                    dados.get("telefone") or None,
                    dados.get("whatsapp") or None,
                    dados.get("endereco") or None,
                    dados.get("cidade") or None,
                    dados.get("uf") or None,
                    dados.get("cep") or None,
                    dados.get("vendedor_id") or None,
                    dados.get("limite_credito") or 0,
                    dados.get("observacoes") or None,
                    cliente_id,
                ),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def set_ativo(self, cliente_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE clientes SET ativo=?, atualizado_em=datetime('now')"
                " WHERE id=?",
                (int(ativo), cliente_id),
            )
            return cur.rowcount > 0

    # ── Endereços ──────────────────────────────────────────

    def listar_enderecos(self, cliente_id: int) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM cliente_enderecos WHERE cliente_id=? ORDER BY tipo", (cliente_id,)
            ).fetchall()]

    def criar_endereco(self, cliente_id: int, dados: dict) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO cliente_enderecos (cliente_id, tipo, cep, logradouro, numero, complemento, bairro, cidade, uf)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (cliente_id, dados["tipo"], dados.get("cep", ""), dados.get("logradouro", ""),
                 dados.get("numero", ""), dados.get("complemento", ""), dados.get("bairro", ""),
                 dados.get("cidade", ""), dados.get("uf", "")),
            )
            return cur.lastrowid

    def excluir_endereco(self, endereco_id: int) -> bool:
        with system_conn() as conn:
            return conn.execute("DELETE FROM cliente_enderecos WHERE id=?", (endereco_id,)).rowcount > 0

    # ── Contatos ───────────────────────────────────────────

    def listar_contatos(self, cliente_id: int) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM cliente_contatos WHERE cliente_id=? ORDER BY nome", (cliente_id,)
            ).fetchall()]

    def criar_contato(self, cliente_id: int, dados: dict) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO cliente_contatos (cliente_id, nome, cargo, telefone, email) VALUES (?,?,?,?,?)",
                (cliente_id, dados["nome"], dados.get("cargo", ""),
                 dados.get("telefone", ""), dados.get("email", "")),
            )
            return cur.lastrowid

    def excluir_contato(self, contato_id: int) -> bool:
        with system_conn() as conn:
            return conn.execute("DELETE FROM cliente_contatos WHERE id=?", (contato_id,)).rowcount > 0

    # ── Apoio Comercial ────────────────────────────────────

    def get_apoio_comercial(self, cliente_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM cliente_apoio_comercial WHERE cliente_id=?", (cliente_id,)).fetchone()
            return dict(row) if row else None

    def upsert_apoio_comercial(self, cliente_id: int, dados: dict) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO cliente_apoio_comercial (cliente_id, condicao_pagamento_id, tabela_preco_id, limite_credito, transportadora)"
                " VALUES (?,?,?,?,?) ON CONFLICT(cliente_id) DO UPDATE SET"
                " condicao_pagamento_id=excluded.condicao_pagamento_id,"
                " tabela_preco_id=excluded.tabela_preco_id,"
                " limite_credito=excluded.limite_credito,"
                " transportadora=excluded.transportadora",
                (cliente_id, dados.get("condicao_pagamento_id"), dados.get("tabela_preco_id"),
                 float(dados.get("limite_credito") or 0), dados.get("transportadora", "")),
            )
            return cur.lastrowid

    # ── Apoio Fiscal ───────────────────────────────────────

    def get_apoio_fiscal(self, cliente_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM cliente_apoio_fiscal WHERE cliente_id=?", (cliente_id,)).fetchone()
            return dict(row) if row else None

    def upsert_apoio_fiscal(self, cliente_id: int, dados: dict) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO cliente_apoio_fiscal (cliente_id, cfop_padrao, cst_icms, cst_pis, cst_cofins, aliquota_icms, aliquota_pis, aliquota_cofins)"
                " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(cliente_id) DO UPDATE SET"
                " cfop_padrao=excluded.cfop_padrao, cst_icms=excluded.cst_icms,"
                " cst_pis=excluded.cst_pis, cst_cofins=excluded.cst_cofins,"
                " aliquota_icms=excluded.aliquota_icms, aliquota_pis=excluded.aliquota_pis,"
                " aliquota_cofins=excluded.aliquota_cofins",
                (cliente_id, dados.get("cfop_padrao", ""), dados.get("cst_icms", ""),
                 dados.get("cst_pis", ""), dados.get("cst_cofins", ""),
                 float(dados.get("aliquota_icms") or 0), float(dados.get("aliquota_pis") or 0),
                 float(dados.get("aliquota_cofins") or 0)),
            )
            return cur.lastrowid


cliente_repo = ClienteRepository()