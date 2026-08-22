from __future__ import annotations

from catalog_server.db import system_conn


class InteracaoRepository:

    def list(self, cliente_id: int | None = None, pendentes: bool = False, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM cliente_interacao WHERE 1=1"
        args: list = []
        if cliente_id:
            sql += " AND cliente_id = ?"
            args.append(cliente_id)
        if pendentes:
            sql += " AND data_proximo_contato IS NOT NULL AND data_proximo_contato <= date('now')"
        sql += " ORDER BY data_contato DESC, id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(
        self, cliente_id: int | None, cliente_nome: str, tipo: str,
        descricao: str, data_contato: str,
        data_proximo_contato: str | None = None,
        orcamento_id: int | None = None, usuario_id: int | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO cliente_interacao (cliente_id, cliente_nome, tipo, descricao,"
                " data_contato, data_proximo_contato, orcamento_id, usuario_id)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (cliente_id, cliente_nome.strip(), tipo, descricao.strip(),
                 data_contato, data_proximo_contato, orcamento_id, usuario_id),
            )
            return cur.lastrowid


class GarantiaRepository:

    def list(self, cliente_id: int | None = None, status: str | None = None) -> list[dict]:
        sql = "SELECT * FROM garantia WHERE 1=1"
        args: list = []
        if cliente_id:
            sql += " AND cliente_id = ?"
            args.append(cliente_id)
        if status:
            sql += " AND status = ?"
            args.append(status)
        sql += " ORDER BY data_fim, cliente_nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(
        self, cliente_nome: str, produto_nome: str, data_inicio: str, data_fim: str,
        dias: int = 90, cliente_id: int | None = None,
        orcamento_id: int | None = None, variante_id: int | None = None,
        descricao: str = "", observacao: str = "",
        data_venda: str | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO garantia (cliente_nome, cliente_id, orcamento_id, variante_id,"
                " produto_nome, data_venda, data_inicio, data_fim, dias, descricao, observacao)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (cliente_nome.strip(), cliente_id, orcamento_id, variante_id,
                 produto_nome.strip(), data_venda, data_inicio, data_fim, dias,
                 descricao, observacao),
            )
            return cur.lastrowid

    def update_status(self, garantia_id: int, status: str) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE garantia SET status=? WHERE id=?", (status, garantia_id)
            )
            return cur.rowcount > 0


interacao_repo = InteracaoRepository()
garantia_repo = GarantiaRepository()
