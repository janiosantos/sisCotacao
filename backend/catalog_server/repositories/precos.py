from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories.busca import codigo_adicional_sql


class TabelaPrecoRepository:

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM tabelas_preco"
        args: list = []
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, tabela_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM tabelas_preco WHERE id=?", (tabela_id,)).fetchone()
            return dict(row) if row else None

    def create(
        self, nome: str, tipo: str = "varejo", margem: float = 0,
        markup: float = 0, metodologia: str = "divisor",
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO tabelas_preco (nome, tipo, margem_padrao, markup, metodologia) VALUES (?,?,?,?,?)",
                (nome.strip(), tipo, margem, markup, metodologia),
            )
            return cur.lastrowid

    def update(
        self, tabela_id: int, nome: str, tipo: str, margem: float,
        markup: float, metodologia: str = "divisor",
    ) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE tabelas_preco SET nome=?, tipo=?, margem_padrao=?, markup=?, metodologia=?,"
                " atualizado_em=datetime('now') WHERE id=?",
                (nome.strip(), tipo, margem, markup, metodologia, tabela_id),
            )
            return cur.rowcount > 0

    def set_ativo(self, tabela_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE tabelas_preco SET ativo=?, atualizado_em=datetime('now') WHERE id=?",
                (int(ativo), tabela_id),
            )
            return cur.rowcount > 0

    def list_itens(self, tabela_id: int, termo: str | None = None) -> list[dict]:
        sql = (
            "SELECT i.*, p.sku, p.preco AS preco_base, p.custo_unitario,"
            " p.nome AS produto_nome, p.marca"
            " FROM tabela_preco_itens i"
            " JOIN produtos_cadastro p ON p.id = i.produto_id"
            " WHERE i.tabela_id = ?"
        )
        args: list = [tabela_id]
        if termo:
            sql += (
                " AND (f_unaccent(p.nome) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.sku) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.marca) ILIKE f_unaccent(?) "
                f"OR {codigo_adicional_sql('p.id')})"
            )
            like = f"%{termo}%"
            args.extend([like, like, like, like])
        sql += " ORDER BY p.nome, p.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert_item(self, tabela_id: int, produto_id: int, preco: float, margem: float | None = None) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO tabela_preco_itens (tabela_id, produto_id, preco, margem)"
                " VALUES (?,?,?,?)"
                " ON CONFLICT(tabela_id, produto_id) DO UPDATE SET preco=excluded.preco, margem=excluded.margem",
                (tabela_id, produto_id, preco, margem),
            )
            return cur.rowcount > 0

    def delete_item(self, tabela_id: int, produto_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "DELETE FROM tabela_preco_itens WHERE tabela_id=? AND produto_id=?",
                (tabela_id, produto_id),
            )
            return cur.rowcount > 0

    def gerar_precos(self, tabela_id: int, margem: float | None = None, markup: float | None = None) -> int:
        # Este endpoint é legado e mantém a fórmula histórica da tela de
        # tabelas. O reajuste auditado que consome despesas/competências usa
        # pricing_engine.previa_reajuste/aplicar_reajuste.
        from catalog_server.services import pricing_engine

        with system_conn() as conn:
            tab = conn.execute("SELECT * FROM tabelas_preco WHERE id=?", (tabela_id,)).fetchone()
            if not tab:
                return 0
            variantes = conn.execute(
                "SELECT id, custo_unitario, preco FROM produtos_cadastro WHERE custo_unitario IS NOT NULL AND custo_unitario > 0"
            ).fetchall()
            count = 0
            for v in variantes:
                vid = v["id"]
                calc = pricing_engine.calcular_preco(
                    vid,
                    tabela_id=tabela_id,
                    margem=margem,
                    markup=markup,
                    despesas_fixas_pct=0,
                    cartao_pct=0,
                    impostos_pct=0,
                )
                novo_preco = calc.get("preco_sugerido")
                if novo_preco is None or novo_preco <= 0:
                    continue
                conn.execute(
                    "INSERT INTO tabela_preco_itens (tabela_id, produto_id, preco, margem)"
                    " VALUES (?,?,?,?)"
                    " ON CONFLICT(tabela_id, produto_id) DO UPDATE SET preco=excluded.preco, margem=excluded.margem",
                    (tabela_id, vid, round(novo_preco, 2), calc.get("margem_efetiva_pct")),
                )
                count += 1
            return count


class PromocaoRepository:

    def list(self, ativo: bool | None = None) -> list[dict]:
        sql = "SELECT * FROM promocoes"
        args: list = []
        if ativo is not None:
            sql += " WHERE ativo = ?"
            args.append(int(ativo))
        sql += " ORDER BY data_inicio DESC, data_fim DESC, nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, promocao_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM promocoes WHERE id=?", (promocao_id,)).fetchone()
            return dict(row) if row else None

    def create(
        self, nome: str, tipo: str, valor: float,
        data_inicio: str | None = None, data_fim: str | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO promocoes (nome, tipo, valor, data_inicio, data_fim) VALUES (?,?,?,?,?)",
                (nome.strip(), tipo, valor, data_inicio, data_fim),
            )
            return cur.lastrowid

    def update(
        self, promocao_id: int, nome: str, tipo: str, valor: float,
        data_inicio: str | None = None, data_fim: str | None = None, ativo: int = 1,
    ) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE promocoes SET nome=?, tipo=?, valor=?, data_inicio=?, data_fim=?, ativo=? WHERE id=?",
                (nome.strip(), tipo, valor, data_inicio, data_fim, ativo, promocao_id),
            )
            return cur.rowcount > 0

    def list_itens(self, promocao_id: int, termo: str | None = None) -> list[dict]:
        sql = (
            "SELECT i.*, p.sku, p.preco AS preco_base,"
            " p.nome AS produto_nome, p.marca"
            " FROM promocao_itens i"
            " JOIN produtos_cadastro p ON p.id = i.produto_id"
            " WHERE i.promocao_id = ?"
        )
        args: list = [promocao_id]
        if termo:
            sql += (
                " AND (f_unaccent(p.nome) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.sku) ILIKE f_unaccent(?) "
                f"OR {codigo_adicional_sql('p.id')})"
            )
            like = f"%{termo}%"
            args.extend([like, like, like])
        sql += " ORDER BY p.nome, p.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert_item(self, promocao_id: int, produto_id: int, preco_promocional: float) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO promocao_itens (promocao_id, produto_id, preco_promocional)"
                " VALUES (?,?,?)"
                " ON CONFLICT(promocao_id, produto_id) DO UPDATE SET preco_promocional=excluded.preco_promocional",
                (promocao_id, produto_id, preco_promocional),
            )
            return cur.rowcount > 0

    def delete_item(self, promocao_id: int, produto_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "DELETE FROM promocao_itens WHERE promocao_id=? AND produto_id=?",
                (promocao_id, produto_id),
            )
            return cur.rowcount > 0

    def aplicar_promocao(
        self, promocao_id: int, produto_ids: list[int],
        tipo: str, valor: float,
    ) -> int:
        count = 0
        for vid in produto_ids:
            preco_prom = None
            if tipo == "valor_fixo":
                preco_prom = valor
            elif tipo == "percentual":
                with system_conn() as conn:
                    row = conn.execute("SELECT preco FROM produtos_cadastro WHERE id=?", (vid,)).fetchone()
                    if row:
                        preco_prom = round(float(row["preco"] or 0) * (1 - valor / 100), 2)
            if preco_prom is not None and preco_prom > 0:
                self.upsert_item(promocao_id, vid, preco_prom)
                count += 1
        return count


tabela_preco_repo = TabelaPrecoRepository()
promocao_repo = PromocaoRepository()


class RevisaoRepository:

    def list(self, tabela_id: int | None = None) -> list[dict]:
        sql = (
            "SELECT r.*, t.nome AS tabela_nome, c.nome AS cliente_nome"
            " FROM precificacao_revisoes r"
            " JOIN tabelas_preco t ON t.id = r.tabela_id"
            " LEFT JOIN clientes c ON c.id = r.cliente_id"
        )
        args: list = []
        if tabela_id:
            sql += " WHERE r.tabela_id = ?"
            args.append(tabela_id)
        sql += " ORDER BY r.data_cadastro DESC"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, revisao_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT r.*, t.nome AS tabela_nome, c.nome AS cliente_nome"
                " FROM precificacao_revisoes r"
                " JOIN tabelas_preco t ON t.id = r.tabela_id"
                " LEFT JOIN clientes c ON c.id = r.cliente_id"
                " WHERE r.id = ?", (revisao_id,)
            ).fetchone()
            return dict(row) if row else None

    def create(self, tabela_id: int, codigo: str, descricao: str = "",
               data_validade: str | None = None, cliente_id: int | None = None) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO precificacao_revisoes (tabela_id, codigo, descricao, data_validade, cliente_id)"
                " VALUES (?,?,?,?,?)",
                (tabela_id, codigo.strip(), descricao.strip(), data_validade, cliente_id),
            )
            return cur.lastrowid

    def fechar(self, revisao_id: int) -> bool:
        with system_conn() as conn:
            return conn.execute(
                "UPDATE precificacao_revisoes SET situacao='fechada' WHERE id=? AND situacao='aberta'",
                (revisao_id,),
            ).rowcount > 0

    def list_itens_com_margem(self, tabela_id: int, termo: str | None = None) -> list[dict]:
        sql = (
            "SELECT i.*, p.sku, p.preco AS preco_base, p.custo_unitario,"
            " p.nome AS produto_nome, p.marca,"
            " CASE WHEN i.preco > 0 AND (p.custo_unitario > 0)"
            "  THEN ROUND(((i.preco - p.custo_unitario) / i.preco) * 100, 2)"
            "  ELSE NULL END AS margem_pct"
            " FROM tabela_preco_itens i"
            " JOIN produtos_cadastro p ON p.id = i.produto_id"
            " WHERE i.tabela_id = ?"
        )
        args: list = [tabela_id]
        if termo:
            sql += (
                " AND (f_unaccent(p.nome) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.sku) ILIKE f_unaccent(?) "
                f"OR {codigo_adicional_sql('p.id')})"
            )
            like = f"%{termo}%"
            args.extend([like, like, like])
        sql += " ORDER BY p.nome, p.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


revisao_repo = RevisaoRepository()


class PrecoHistoricoRepository:

    def list(
        self,
        tabela_id: int | None = None,
        produto_id: int | None = None,
        termo: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        sql = (
            "SELECT h.*, p.sku, p.nome AS produto_nome, p.marca, t.nome AS tabela_nome,"
            " u.nome AS usuario_nome"
            " FROM preco_historico h"
            " JOIN produtos_cadastro p ON p.id = h.produto_id"
            " JOIN tabelas_preco t ON t.id = h.tabela_id"
            " LEFT JOIN usuarios u ON u.id = h.usuario_id"
        )
        conds, args = [], []
        if tabela_id:
            conds.append("h.tabela_id=?")
            args.append(tabela_id)
        if produto_id:
            conds.append("h.produto_id=?")
            args.append(produto_id)
        if termo:
            like = f"%{termo}%"
            conds.append(
                "(f_unaccent(p.nome) ILIKE f_unaccent(?) "
                "OR f_unaccent(p.sku) ILIKE f_unaccent(?) OR t.nome ILIKE ? "
                f"OR {codigo_adicional_sql('p.id')})"
            )
            args += [like, like, like, like]
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY h.id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


preco_historico_repo = PrecoHistoricoRepository()
