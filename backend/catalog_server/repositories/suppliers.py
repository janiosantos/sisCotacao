from __future__ import annotations

from catalog_server.db import system_conn


class SupplierRepository:

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM fornecedores"
        if somente_ativos:
            sql += " WHERE ativo=1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]

    # ------------------------------------------------------------------

    def create(
        self,
        nome: str,
        whatsapp: str,
        email: str,
        observacoes: str,
        razao_social: str = "",
        cnpj_cpf: str = "",
        representante: str = "",
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fornecedores (nome, razao_social, cnpj_cpf, representante,"
                " whatsapp, email, observacoes) VALUES (?,?,?,?,?,?,?)",
                (
                    nome,
                    razao_social or None,
                    cnpj_cpf or None,
                    representante or None,
                    whatsapp or None,
                    email or None,
                    observacoes or None,
                ),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(
        self,
        fornecedor_id: int,
        nome: str,
        whatsapp: str,
        email: str,
        observacoes: str,
        razao_social: str = "",
        cnpj_cpf: str = "",
        representante: str = "",
    ) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE fornecedores SET nome=?, whatsapp=?, email=?, observacoes=?,"
                " razao_social=?, cnpj_cpf=?, representante=? WHERE id=?",
                (
                    nome,
                    whatsapp or None,
                    email or None,
                    observacoes or None,
                    razao_social or None,
                    cnpj_cpf or None,
                    representante or None,
                    fornecedor_id,
                ),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def set_ativo(self, fornecedor_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE fornecedores SET ativo=? WHERE id=?",
                (int(ativo), fornecedor_id),
            )
            return cur.rowcount > 0
