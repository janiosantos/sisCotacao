from __future__ import annotations

from catalog_server.db import system_conn


class UsuarioRepository:

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = (
            "SELECT id, nome, login, ativo, desconto_limite_pct,"
            " autoriza_desconto, criado_em FROM usuarios"
        )
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            out = [dict(r) for r in conn.execute(sql).fetchall()]
        for u in out:
            self._anexar_perfis(u)
        return out

    # ------------------------------------------------------------------

    def _anexar_perfis(self, user: dict) -> dict:
        """Anexa perfis RBAC e permissões efetivas ao dict do usuário."""
        from catalog_server.blueprints.api_permissoes import (
            overrides_usuario,
            perfil_ids_usuario,
            permissoes_efetivas,
        )

        user["perfil_ids"] = perfil_ids_usuario(user["id"])
        user["overrides"] = overrides_usuario(user["id"])
        user["permissoes"] = permissoes_efetivas(user["id"])
        return user

    # ------------------------------------------------------------------

    def get(self, usuario_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT id, nome, login, ativo, desconto_limite_pct,"
                " autoriza_desconto, criado_em FROM usuarios"
                " WHERE id = ?",
                (usuario_id,),
            ).fetchone()
            if row is None:
                return None
            return self._anexar_perfis(dict(row))

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
        desconto_limite_pct: float = 0.0,
        autoriza_desconto: bool = False,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO usuarios (nome, login, senha_hash,"
                " desconto_limite_pct, autoriza_desconto)"
                " VALUES (?,?,?,?,?)",
                (
                    nome,
                    login,
                    senha_hash,
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
        senha_hash: str | None = None,
        desconto_limite_pct: float | None = None,
        autoriza_desconto: bool | None = None,
    ) -> bool:
        fields = ["nome=?"]
        params: list = [nome]
        if senha_hash:
            fields.append("senha_hash=?")
            params.append(senha_hash)
            fields.append("token_version=token_version+1")
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

    def esta_ativo(self, usuario_id: int) -> bool:
        """Retorna True se o usuário existe e está ativo."""
        with system_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM usuarios WHERE id=? AND ativo=1",
                (usuario_id,),
            ).fetchone()
            return row is not None

    def set_ativo(self, usuario_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET ativo=?, atualizado_em=datetime('now')"
                " WHERE id=?",
                (int(ativo), usuario_id),
            )
            return cur.rowcount > 0


usuario_repo = UsuarioRepository()
