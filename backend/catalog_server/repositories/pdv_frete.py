from __future__ import annotations

from catalog_server.db import system_conn


class DescontoRepository:

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM politica_descontos"
        args: list = []
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(self, nome: str, tipo: str, valor_maximo: float, valor_minimo: float = 0, perfil: str = "") -> int:
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO politica_descontos (nome, tipo, valor_maximo, valor_minimo, perfil) VALUES (?,?,?,?,?)",
                (nome.strip(), tipo, valor_maximo, valor_minimo, perfil),
            ).lastrowid


class FreteRepository:

    def list(self, uf: str | None = None, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM politica_fretes"
        args: list = []
        if uf:
            sql += " WHERE (uf = ? OR uf = '')"
            args.append(uf)
        if somente_ativos:
            sql += " WHERE ativo = 1" if "WHERE" not in sql else " AND ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(self, nome: str, uf: str, valor_frete: float, valor_minimo_pedido: float = 0, tipo: str = "fixo") -> int:
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO politica_fretes (nome, uf, valor_frete, valor_minimo_pedido, tipo) VALUES (?,?,?,?,?)",
                (nome.strip(), uf, valor_frete, valor_minimo_pedido, tipo),
            ).lastrowid


desconto_repo = DescontoRepository()
frete_repo = FreteRepository()
