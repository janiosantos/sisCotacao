from __future__ import annotations

from catalog_server.db import system_conn

# Categorias de referência para o cadastro de fornecedores (filtros/agrupamento).
CATEGORIAS = [
    "elétrico",
    "hidráulico",
    "ferramentas",
    "construção",
    "revestimento",
    "madeira",
    "tintas",
    "fixadores",
    "acabamento",
    "segurança",
    "geral",
]


class SupplierRepository:

    def list(
        self,
        somente_ativos: bool = False,
        categoria: str | None = None,
        termo: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM fornecedores"
        where: list[str] = []
        args: list = []
        if somente_ativos:
            where.append("ativo = 1")
        if categoria:
            where.append("categoria = ?")
            args.append(categoria)
        if termo:
            like = f"%{termo.strip()}%"
            where.append(
                "(nome LIKE ? COLLATE NOCASE OR razao_social LIKE ? COLLATE NOCASE"
                " OR cnpj_cpf LIKE ? OR cidade LIKE ? OR representante LIKE ? COLLATE NOCASE)"
            )
            args += [like, like, like, like, like]
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    # ------------------------------------------------------------------

    def get(self, fornecedor_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM fornecedores WHERE id=?", (fornecedor_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------

    def create(self, dados: dict) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fornecedores (nome, razao_social, cnpj_cpf, representante,"
                " whatsapp, email, observacoes, telefone, endereco, numero, bairro,"
                " cidade, uf, cep, categoria, condicao_pagamento_id, prazo_entrega_dias,"
                " nota) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    dados["nome"],
                    (dados.get("razao_social") or "").strip() or None,
                    (dados.get("cnpj_cpf") or "").strip() or None,
                    (dados.get("representante") or "").strip() or None,
                    (dados.get("whatsapp") or "").strip() or None,
                    (dados.get("email") or "").strip() or None,
                    (dados.get("observacoes") or "").strip() or None,
                    (dados.get("telefone") or "").strip() or None,
                    (dados.get("endereco") or "").strip() or None,
                    (dados.get("numero") or "").strip() or None,
                    (dados.get("bairro") or "").strip() or None,
                    (dados.get("cidade") or "").strip() or None,
                    (dados.get("uf") or "").strip() or None,
                    (dados.get("cep") or "").strip() or None,
                    (dados.get("categoria") or "geral").strip(),
                    dados.get("condicao_pagamento_id"),
                    int(dados.get("prazo_entrega_dias") or 30),
                    float(dados.get("nota") or 5.0),
                ),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(self, fornecedor_id: int, dados: dict) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE fornecedores SET nome=?, razao_social=?, cnpj_cpf=?, representante=?,"
                " whatsapp=?, email=?, observacoes=?, telefone=?, endereco=?, numero=?,"
                " bairro=?, cidade=?, uf=?, cep=?, categoria=?, condicao_pagamento_id=?,"
                " prazo_entrega_dias=?, nota=?, atualizado_em=datetime('now') WHERE id=?",
                (
                    dados["nome"],
                    (dados.get("razao_social") or "").strip() or None,
                    (dados.get("cnpj_cpf") or "").strip() or None,
                    (dados.get("representante") or "").strip() or None,
                    (dados.get("whatsapp") or "").strip() or None,
                    (dados.get("email") or "").strip() or None,
                    (dados.get("observacoes") or "").strip() or None,
                    (dados.get("telefone") or "").strip() or None,
                    (dados.get("endereco") or "").strip() or None,
                    (dados.get("numero") or "").strip() or None,
                    (dados.get("bairro") or "").strip() or None,
                    (dados.get("cidade") or "").strip() or None,
                    (dados.get("uf") or "").strip() or None,
                    (dados.get("cep") or "").strip() or None,
                    (dados.get("categoria") or "geral").strip(),
                    dados.get("condicao_pagamento_id"),
                    int(dados.get("prazo_entrega_dias") or 30),
                    float(dados.get("nota") or 5.0),
                    fornecedor_id,
                ),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def set_ativo(self, fornecedor_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE fornecedores SET ativo=?, atualizado_em=datetime('now') WHERE id=?",
                (int(ativo), fornecedor_id),
            )
            return cur.rowcount > 0

    # ── Contatos ───────────────────────────────────────────

    def listar_contatos(self, fornecedor_id: int) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM fornecedor_contatos WHERE fornecedor_id=? ORDER BY nome",
                (fornecedor_id,),
            ).fetchall()]

    def criar_contato(self, fornecedor_id: int, dados: dict) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fornecedor_contatos (fornecedor_id, nome, cargo, telefone, email)"
                " VALUES (?,?,?,?,?)",
                (fornecedor_id, dados["nome"], dados.get("cargo", ""),
                 dados.get("telefone", ""), dados.get("email", "")),
            )
            return cur.lastrowid

    def excluir_contato(self, contato_id: int) -> bool:
        with system_conn() as conn:
            return conn.execute(
                "DELETE FROM fornecedor_contatos WHERE id=?", (contato_id,)
            ).rowcount > 0


supplier_repo = SupplierRepository()