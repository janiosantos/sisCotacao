from __future__ import annotations

from catalog_server.db import system_conn


class UsuarioRepository:

    PERFIS = ("admin", "vendedor")

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT id, nome, login, perfil, ativo, criado_em FROM usuarios"
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]

    # ------------------------------------------------------------------

    def get(self, usuario_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT id, nome, login, perfil, ativo, criado_em FROM usuarios"
                " WHERE id = ?",
                (usuario_id,),
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------

    def get_by_login(self, login: str) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE login = ?", (login,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------

    def count(self) -> int:
        with system_conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()
            return int(row["n"])

    # ------------------------------------------------------------------

    def create(self, nome: str, login: str, senha_hash: str, perfil: str) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO usuarios (nome, login, senha_hash, perfil)"
                " VALUES (?,?,?,?)",
                (nome, login, senha_hash, perfil),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(
        self,
        usuario_id: int,
        nome: str,
        perfil: str,
        senha_hash: str | None = None,
    ) -> bool:
        with system_conn() as conn:
            if senha_hash:
                cur = conn.execute(
                    "UPDATE usuarios SET nome=?, perfil=?, senha_hash=?,"
                    " atualizado_em=datetime('now') WHERE id=?",
                    (nome, perfil, senha_hash, usuario_id),
                )
            else:
                cur = conn.execute(
                    "UPDATE usuarios SET nome=?, perfil=?,"
                    " atualizado_em=datetime('now') WHERE id=?",
                    (nome, perfil, usuario_id),
                )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def set_ativo(self, usuario_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET ativo=?, atualizado_em=datetime('now')"
                " WHERE id=?",
                (int(ativo), usuario_id),
            )
            return cur.rowcount > 0


usuario_repo = UsuarioRepository()