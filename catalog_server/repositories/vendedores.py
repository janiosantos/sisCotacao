from __future__ import annotations

from catalog_server.db import system_conn


class VendedorRepository:

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM vendedores"
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]

    # ------------------------------------------------------------------

    def get(self, vendedor_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM vendedores WHERE id = ?", (vendedor_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------

    def create(self, nome: str, comissao_pct: float) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO vendedores (nome, comissao_pct) VALUES (?,?)",
                (nome, comissao_pct),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(self, vendedor_id: int, nome: str, comissao_pct: float) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE vendedores SET nome=?, comissao_pct=?, atualizado_em="
                " datetime('now') WHERE id=?",
                (nome, comissao_pct, vendedor_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def set_ativo(self, vendedor_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE vendedores SET ativo=?, atualizado_em=datetime('now')"
                " WHERE id=?",
                (int(ativo), vendedor_id),
            )
            return cur.rowcount > 0


vendedor_repo = VendedorRepository()