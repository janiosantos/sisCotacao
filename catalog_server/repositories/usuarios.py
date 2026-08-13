from __future__ import annotations

from catalog_server.db import system_conn


class UsuarioRepository:

    PERFIS = ("admin", "vendedor")

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = (
            "SELECT id, nome, login, perfil, ativo, desconto_limite_pct,"
            " autoriza_desconto, criado_em FROM usuarios"
        )
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]

    # ------------------------------------------------------------------

    def get(self, usuario_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT id, nome, login, perfil, ativo, desconto_limite_pct,"
                " autoriza_desconto, criado_em FROM usuarios"
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

    def create(
        self,
        nome: str,
        login: str,
        senha_hash: str,
        perfil: str,
        desconto_limite_pct: float = 0.0,
        autoriza_desconto: bool = False,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO usuarios (nome, login, senha_hash, perfil,"
                " desconto_limite_pct, autoriza_desconto)"
                " VALUES (?,?,?,?,?,?)",
                (
                    nome,
                    login,
                    senha_hash,
                    perfil,
                    max(0.0, float(desconto_limite_pct or 0)),
                    1 if autoriza_desconto else 0,
                ),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(
        self,
        usuario_id: int,
        nome: str,
        perfil: str,
        senha_hash: str | None = None,
        desconto_limite_pct: float | None = None,
        autoriza_desconto: bool | None = None,
    ) -> bool:
        fields = ["nome=?", "perfil=?"]
        params: list = [nome, perfil]
        if senha_hash:
            fields.append("senha_hash=?")
            params.append(senha_hash)
        if desconto_limite_pct is not None:
            fields.append("desconto_limite_pct=?")
            params.append(max(0.0, float(desconto_limite_pct)))
        if autoriza_desconto is not None:
            fields.append("autoriza_desconto=?")
            params.append(1 if autoriza_desconto else 0)
        params.append(usuario_id)
        with system_conn() as conn:
            cur = conn.execute(
                f"UPDATE usuarios SET {', '.join(fields)},"
                " atualizado_em=datetime('now') WHERE id=?",
                params,
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