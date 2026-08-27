from __future__ import annotations

from catalog_server.db import system_conn


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

    def create(self, nome: str, tipo: str = "varejo", margem: float = 0, markup: float = 0) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO tabelas_preco (nome, tipo, margem_padrao, markup) VALUES (?,?,?,?)",
                (nome.strip(), tipo, margem, markup),
            )
            return cur.lastrowid

    def update(self, tabela_id: int, nome: str, tipo: str, margem: float, markup: float) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE tabelas_preco SET nome=?, tipo=?, margem_padrao=?, markup=?,"
                " atualizado_em=datetime('now') WHERE id=?",
                (nome.strip(), tipo, margem, markup, tabela_id),
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
            sql += " AND (p.nome LIKE ? OR p.sku LIKE ? OR p.marca LIKE ?)"
            like = f"%{termo}%"
            args.extend([like, like, like])
        sql += " ORDER BY p.nome, p.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert_item(self, tabela_id: int, variante_id: int, preco: float, margem: float | None = None) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO tabela_preco_itens (tabela_id, produto_id, preco, margem)"
                " VALUES (?,?,?,?)"
                " ON CONFLICT(tabela_id, produto_id) DO UPDATE SET preco=excluded.preco, margem=excluded.margem",
                (tabela_id, variante_id, preco, margem),
            )
            return cur.rowcount > 0

    def delete_item(self, tabela_id: int, variante_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "DELETE FROM tabela_preco_itens WHERE tabela_id=? AND produto_id=?",
                (tabela_id, variante_id),
            )
            return cur.rowcount > 0

    def gerar_precos(self, tabela_id: int, margem: float | None = None, markup: float | None = None) -> int:
        with system_conn() as conn:
            tab = conn.execute("SELECT * FROM tabelas_preco WHERE id=?", (tabela_id,)).fetchone()
            if not tab:
                return 0
            m = margem if margem is not None else float(tab["margem_padrao"] or 0)
            mk = markup if markup is not None else float(tab["markup"] or 0)
            variantes = conn.execute(
                "SELECT id, custo_unitario, preco FROM produtos_cadastro WHERE custo_unitario IS NOT NULL AND custo_unitario > 0"
            ).fetchall()
            count = 0
            for v in variantes:
                vid = v["id"]
                custo = float(v["custo_unitario"] or 0)
                if mk > 0:
                    novo_preco = custo * (1 + mk / 100)
                elif m > 0:
                    novo_preco = custo / (1 - m / 100)
                else:
                    novo_preco = float(v["preco"] or 0)
                if novo_preco <= 0:
                    continue
                conn.execute(
                    "INSERT INTO tabela_preco_itens (tabela_id, produto_id, preco, margem)"
                    " VALUES (?,?,?,?)"
                    " ON CONFLICT(tabela_id, produto_id) DO UPDATE SET preco=excluded.preco, margem=excluded.margem",
                    (tabela_id, vid, round(novo_preco, 2), round(m, 2)),
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
            sql += " AND (p.nome LIKE ? OR p.sku LIKE ?)"
            like = f"%{termo}%"
            args.extend([like, like])
        sql += " ORDER BY p.nome, p.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert_item(self, promocao_id: int, variante_id: int, preco_promocional: float) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO promocao_itens (promocao_id, produto_id, preco_promocional)"
                " VALUES (?,?,?)"
                " ON CONFLICT(promocao_id, produto_id) DO UPDATE SET preco_promocional=excluded.preco_promocional",
                (promocao_id, variante_id, preco_promocional),
            )
            return cur.rowcount > 0

    def delete_item(self, promocao_id: int, variante_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "DELETE FROM promocao_itens WHERE promocao_id=? AND produto_id=?",
                (promocao_id, variante_id),
            )
            return cur.rowcount > 0

    def aplicar_promocao(
        self, promocao_id: int, variante_ids: list[int],
        tipo: str, valor: float,
    ) -> int:
        count = 0
        for vid in variante_ids:
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
            sql += " AND (p.nome LIKE ? OR p.sku LIKE ?)"
            like = f"%{termo}%"
            args.extend([like, like])
        sql += " ORDER BY p.nome, p.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


revisao_repo = RevisaoRepository()


class PrecoHistoricoRepository:

    def list(
        self,
        tabela_id: int | None = None,
        variante_id: int | None = None,
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
        if variante_id:
            conds.append("h.produto_id=?")
            args.append(variante_id)
        if termo:
            like = f"%{termo}%"
            conds.append("(p.nome LIKE ? OR p.sku LIKE ? OR t.nome LIKE ?)")
            args += [like, like, like]
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY h.id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


preco_historico_repo = PrecoHistoricoRepository()
