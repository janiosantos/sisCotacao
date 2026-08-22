from __future__ import annotations

from catalog_server.db import system_conn


class PlanoContasRepository:

    def list(self, tipo: str | None = None, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM plano_de_contas"
        where: list[str] = []
        args: list = []
        if tipo:
            where.append("tipo = ?")
            args.append(tipo)
        if somente_ativos:
            where.append("ativo = 1")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY codigo, nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    # ------------------------------------------------------------------

    def get(self, conta_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM plano_de_contas WHERE id = ?", (conta_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------

    def create(self, codigo: str, nome: str, tipo: str, pai_id: int | None) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO plano_de_contas (codigo, nome, tipo, pai_id)"
                " VALUES (?,?,?,?)",
                (codigo, nome, tipo, pai_id or None),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(self, conta_id: int, codigo: str, nome: str, tipo: str, pai_id: int | None) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE plano_de_contas SET codigo=?, nome=?, tipo=?, pai_id=?,"
                " atualizado_em=datetime('now') WHERE id=?",
                (codigo, nome, tipo, pai_id or None, conta_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def set_ativo(self, conta_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE plano_de_contas SET ativo=?, atualizado_em=datetime('now')"
                " WHERE id=?",
                (int(ativo), conta_id),
            )
            return cur.rowcount > 0


plano_conta_repo = PlanoContasRepository()