from __future__ import annotations

from catalog_server.db import system_conn


class CfopRepository:

    def list(self, tipo: str | None = None) -> list[dict]:
        sql = "SELECT * FROM cfop"
        args: list = []
        if tipo:
            sql += " WHERE tipo = ?"
            args.append(tipo)
        sql += " ORDER BY codigo"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


class CstRepository:

    def list(self, tabela: str) -> list[dict]:
        sql = f"SELECT * FROM {tabela} ORDER BY codigo"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]


class FiscalConfigRepository:

    def get(self, variante_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT f.*, v.sku, p.nome AS produto_nome, p.marca"
                " FROM fiscal_config f"
                " JOIN variantes v ON v.id = f.variante_id"
                " JOIN produtos_cadastro p ON p.id = v.produto_id"
                " WHERE f.variante_id = ?",
                (variante_id,),
            ).fetchone()
            return dict(row) if row else None

    def upsert(
        self,
        variante_id: int,
        ncm: str | None = None,
        cfop: str | None = None,
        cst_icms: str | None = None,
        cst_pis: str | None = None,
        cst_cofins: str | None = None,
        aliquota_icms: float = 0,
        aliquota_pis: float = 0,
        aliquota_cofins: float = 0,
        aliquota_ipi: float = 0,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fiscal_config (variante_id, ncm, cfop, cst_icms, cst_pis, cst_cofins,"
                " aliquota_icms, aliquota_pis, aliquota_cofins, aliquota_ipi)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(variante_id) DO UPDATE SET"
                " ncm=COALESCE(excluded.ncm, fiscal_config.ncm),"
                " cfop=COALESCE(excluded.cfop, fiscal_config.cfop),"
                " cst_icms=COALESCE(excluded.cst_icms, fiscal_config.cst_icms),"
                " cst_pis=COALESCE(excluded.cst_pis, fiscal_config.cst_pis),"
                " cst_cofins=COALESCE(excluded.cst_cofins, fiscal_config.cst_cofins),"
                " aliquota_icms=COALESCE(excluded.aliquota_icms, fiscal_config.aliquota_icms),"
                " aliquota_pis=COALESCE(excluded.aliquota_pis, fiscal_config.aliquota_pis),"
                " aliquota_cofins=COALESCE(excluded.aliquota_cofins, fiscal_config.aliquota_cofins),"
                " aliquota_ipi=COALESCE(excluded.aliquota_ipi, fiscal_config.aliquota_ipi)",
                (
                    variante_id,
                    ncm or "",
                    cfop,
                    cst_icms,
                    cst_pis,
                    cst_cofins,
                    aliquota_icms,
                    aliquota_pis,
                    aliquota_cofins,
                    aliquota_ipi,
                ),
            )
            return cur.lastrowid if cur.lastrowid else variante_id

    def list(self, page: int = 0, limit: int = 100, termo: str | None = None) -> list[dict]:
        sql = (
            "SELECT f.*, v.sku, v.preco, p.nome AS produto_nome, p.marca,"
            " cat.nome AS categoria"
            " FROM fiscal_config f"
            " JOIN variantes v ON v.id = f.variante_id"
            " JOIN produtos_cadastro p ON p.id = v.produto_id"
            " LEFT JOIN categorias cat ON cat.id = p.categoria_id"
        )
        args: list = []
        if termo:
            sql += " WHERE (p.nome LIKE ? OR v.sku LIKE ? OR f.ncm LIKE ?)"
            like = f"%{termo}%"
            args.extend([like, like, like])
        sql += " ORDER BY p.nome, v.sku LIMIT ? OFFSET ?"
        args.extend([limit, page * limit])
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def gerar_config_padrao(self, cfop_padrao: str = "5.102", cst_icms: str = "00") -> int:
        with system_conn() as conn:
            existentes = {r["variante_id"] for r in conn.execute(
                "SELECT variante_id FROM fiscal_config"
            ).fetchall()}
            variantes = conn.execute("SELECT id, ncm FROM variantes").fetchall()
            count = 0
            for v in variantes:
                if v["id"] in existentes:
                    continue
                conn.execute(
                    "INSERT INTO fiscal_config (variante_id, ncm, cfop, cst_icms, cst_pis, cst_cofins,"
                    " aliquota_icms, aliquota_pis, aliquota_cofins)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (v["id"], v["ncm"] or "", cfop_padrao, cst_icms, "01", "01", 18, 1.65, 7.6),
                )
                count += 1
            return count


cfop_repo = CfopRepository()
cst_repo = CstRepository()
fiscal_config_repo = FiscalConfigRepository()
