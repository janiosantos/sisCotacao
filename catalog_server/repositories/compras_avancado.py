from __future__ import annotations

from catalog_server.db import system_conn


class FornecedorPrecoRepository:

    def list(self, fornecedor_id: int | None = None, variante_id: int | None = None) -> list[dict]:
        sql = (
            "SELECT f.*, v.sku, p.nome AS produto_nome, fn.nome AS fornecedor_nome"
            " FROM fornecedor_preco f"
            " JOIN variantes v ON v.id = f.variante_id"
            " JOIN produtos_cadastro p ON p.id = v.produto_id"
            " JOIN fornecedores fn ON fn.id = f.fornecedor_id WHERE 1=1"
        )
        args: list = []
        if fornecedor_id:
            sql += " AND f.fornecedor_id = ?"; args.append(fornecedor_id)
        if variante_id:
            sql += " AND f.variante_id = ?"; args.append(variante_id)
        sql += " ORDER BY p.nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert(self, fornecedor_id: int, variante_id: int, preco: float, prazo: int | None = None, icms: float = 0, ipi: float = 0) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fornecedor_preco (fornecedor_id, variante_id, preco, prazo_entrega, icms, ipi)"
                " VALUES (?,?,?,?,?,?) ON CONFLICT(fornecedor_id, variante_id) DO UPDATE SET"
                " preco=excluded.preco, prazo_entrega=excluded.prazo_entrega, icms=excluded.icms, ipi=excluded.ipi",
                (fornecedor_id, variante_id, preco, prazo, icms, ipi),
            )
            return cur.lastrowid


class SolicitacaoRepository:

    def list(self, status: str | None = None) -> list[dict]:
        sql = "SELECT s.*, u.nome AS usuario_nome FROM solicitacao_compra s LEFT JOIN usuarios u ON u.id=s.usuario_id"
        args: list = []
        if status:
            sql += " WHERE s.status = ?"; args.append(status)
        sql += " ORDER BY s.id DESC"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(self, codigo: str, descricao: str = "", observacao: str = "", usuario_id: int | None = None) -> int:
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO solicitacao_compra (codigo, descricao, observacao, usuario_id) VALUES (?,?,?,?)",
                (codigo.strip(), descricao.strip(), observacao.strip(), usuario_id),
            ).lastrowid

    def aprovar(self, sc_id: int, aprovador_id: int, status: str = "aprovada") -> bool:
        with system_conn() as conn:
            return conn.execute(
                "UPDATE solicitacao_compra SET status=?, data_aprovacao=datetime('now'), aprovador_id=? WHERE id=?",
                (status, aprovador_id, sc_id),
            ).rowcount > 0

    def add_item(self, sc_id: int, variante_id: int, quantidade: float, justificativa: str = "") -> int:
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO solicitacao_itens (solicitacao_id, variante_id, quantidade, justificativa) VALUES (?,?,?,?)",
                (sc_id, variante_id, quantidade, justificativa.strip()),
            ).lastrowid


fornecedor_preco_repo = FornecedorPrecoRepository()
solicitacao_repo = SolicitacaoRepository()


class FornecedorPreferencialRepository:

    def list(self, variante_id: int | None = None) -> list[dict]:
        sql = (
            "SELECT f.*, fn.nome AS fornecedor_nome, v.sku, p.nome AS produto_nome"
            " FROM fornecedor_preferencial f"
            " JOIN fornecedores fn ON fn.id = f.fornecedor_id"
            " JOIN variantes v ON v.id = f.variante_id"
            " JOIN produtos_cadastro p ON p.id = v.produto_id"
        )
        args: list = []
        if variante_id:
            sql += " WHERE f.variante_id = ?"; args.append(variante_id)
        sql += " ORDER BY f.ranking, fn.nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert(self, variante_id: int, fornecedor_id: int, ranking: int = 1, preco: float | None = None, prazo: int | None = None) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fornecedor_preferencial (variante_id, fornecedor_id, ranking, ultimo_preco, ultimo_prazo)"
                " VALUES (?,?,?,?,?) ON CONFLICT(variante_id, fornecedor_id) DO UPDATE SET"
                " ranking=excluded.ranking, ultimo_preco=excluded.ultimo_preco, ultimo_prazo=excluded.ultimo_prazo",
                (variante_id, fornecedor_id, ranking, preco, prazo),
            )
            return cur.lastrowid


class ToleranciaRepository:

    def get(self, fornecedor_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM tolerancias_compra WHERE fornecedor_id=?", (fornecedor_id,)).fetchone()
            return dict(row) if row else None

    def upsert(self, fornecedor_id: int, tolerancia_preco_pct: float = 10, tolerancia_qtd_pct: float = 10, exige_aprovacao: bool = True) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO tolerancias_compra (fornecedor_id, tolerancia_preco_pct, tolerancia_qtd_pct, exige_aprovacao)"
                " VALUES (?,?,?,?) ON CONFLICT(fornecedor_id) DO UPDATE SET"
                " tolerancia_preco_pct=excluded.tolerancia_preco_pct, tolerancia_qtd_pct=excluded.tolerancia_qtd_pct, exige_aprovacao=excluded.exige_aprovacao",
                (fornecedor_id, tolerancia_preco_pct, tolerancia_qtd_pct, int(exige_aprovacao)),
            )
            return cur.lastrowid


class IbptRepository:

    def list(self, ncm: str | None = None, limit: int = 100) -> list[dict]:
        sql = "SELECT * FROM ibpt"
        args: list = []
        if ncm:
            sql += " WHERE ncm LIKE ?"; args.append(f"%{ncm}%")
        sql += " ORDER BY ncm LIMIT ?"; args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert(self, ncm: str, descricao: str = "", aliquota_federal: float = 0, aliquota_estadual: float = 0, aliquota_municipal: float = 0) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO ibpt (ncm, descricao, aliquota_federal, aliquota_estadual, aliquota_municipal)"
                " VALUES (?,?,?,?,?) ON CONFLICT(ncm) DO UPDATE SET"
                " descricao=excluded.descricao, aliquota_federal=excluded.aliquota_federal,"
                " aliquota_estadual=excluded.aliquota_estadual, aliquota_municipal=excluded.aliquota_municipal",
                (ncm.strip(), descricao.strip(), aliquota_federal, aliquota_estadual, aliquota_municipal),
            )
            return cur.lastrowid


fornecedor_preferencial_repo = FornecedorPreferencialRepository()
tolerancia_repo = ToleranciaRepository()
ibpt_repo = IbptRepository()
