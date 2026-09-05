from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories.busca import codigo_adicional_sql


class DiagnosticoRepository:
    def resumo(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT classificacao, COUNT(*) AS produtos, SUM(n_variantes) AS variantes "
                "FROM produto_diagnostico_variacao GROUP BY classificacao ORDER BY classificacao"
            ).fetchall()]

    def list(self, classificacao: str | None = None, revisado: bool | None = None, termo: str | None = None, limit: int = 100) -> list[dict]:
        sql = (
            "SELECT d.*, p.nome, p.marca, p.categoria_id "
            "FROM produto_diagnostico_variacao d "
            "JOIN produtos_cadastro p ON p.id = d.produto_id"
        )
        where: list[str] = []
        args: list = []
        if classificacao:
            where.append("d.classificacao = ?")
            args.append(classificacao)
        if revisado is not None:
            where.append("d.revisado = ?")
            args.append(int(revisado))
        if termo:
            where.append(
                "(f_unaccent(p.nome) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.marca) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.sku) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.ean) ILIKE f_unaccent(?) "
                f"OR {codigo_adicional_sql('p.id')})"
            )
            like = f"%{termo}%"
            args.extend([like, like, like, like, like])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY d.n_variantes DESC, p.nome LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def detalhes(self, produto_id: int) -> dict:
        with system_conn() as conn:
            produto = conn.execute(
                "SELECT id, nome, marca, familia_id FROM produtos_cadastro WHERE id = ?", (produto_id,)
            ).fetchone()
            variantes = conn.execute(
                "SELECT id, sku, ean, preco, atributos "
                "FROM produtos_cadastro WHERE id=? AND ativo=1", (produto_id,)
            ).fetchall()
            return {"produto": dict(produto) if produto else None, "variantes": [dict(v) for v in variantes]}

    def marcar_revisado(self, produto_id: int, revisado: bool = True) -> bool:
        with system_conn() as conn:
            return conn.execute(
                "UPDATE produto_diagnostico_variacao SET revisado=?, atualizado_em=datetime('now') WHERE produto_id=?",
                (int(revisado), produto_id),
            ).rowcount > 0

    def consolidar_ofertas(self, produto_id: int, principal_id: int) -> dict:
        """Consolidação de ofertas (variantes) — não se aplica mais.

        A tabela `variantes` foi eliminada e cada antiga variante é agora um
        produto independente em `produtos_cadastro`. Como um produto não possui
        mais variantes-filhas, não há ofertas duplicadas a consolidar.
        """
        raise ValueError("A consolidação de ofertas não se aplica mais: cada produto é independente (tabela variantes eliminada)")


diagnostico_repo = DiagnosticoRepository()
