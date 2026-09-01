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

    def get(self, produto_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT f.*, p.sku, p.nome AS produto_nome, p.marca"
                " FROM fiscal_config f"
                " JOIN produtos_cadastro p ON p.id = f.produto_id"
                " WHERE f.produto_id = ?",
                (produto_id,),
            ).fetchone()
            return dict(row) if row else None

    def upsert(
        self,
        produto_id: int,
        ncm: str | None = None,
        cfop: str | None = None,
        cst_icms: str | None = None,
        cst_pis: str | None = None,
        cst_cofins: str | None = None,
        aliquota_icms: float | None = None,
        aliquota_pis: float | None = None,
        aliquota_cofins: float | None = None,
        aliquota_ipi: float | None = None,
        origem: int | None = None,
        cest: str | None = None,
        csosn: str | None = None,
        aliquota_icms_st: float | None = None,
        mva: float | None = None,
        base_reducao: float | None = None,
        aliquota_interestadual: float | None = None,
        aliquota_fecp: float | None = None,
        credito_icms: float | None = None,
        beneficio_id: int | None = None,
        vigencia_inicio: str | None = None,
        vigencia_fim: str | None = None,
    ) -> int:
        texto = {
            "ncm": ncm, "cfop": cfop, "cst_icms": cst_icms, "cst_pis": cst_pis,
            "cst_cofins": cst_cofins, "cest": cest, "csosn": csosn,
            "vigencia_inicio": vigencia_inicio, "vigencia_fim": vigencia_fim,
        }
        numeros = {
            "aliquota_icms": aliquota_icms, "aliquota_pis": aliquota_pis,
            "aliquota_cofins": aliquota_cofins, "aliquota_ipi": aliquota_ipi,
            "origem": origem, "aliquota_icms_st": aliquota_icms_st, "mva": mva,
            "base_reducao": base_reducao, "aliquota_interestadual": aliquota_interestadual,
            "aliquota_fecp": aliquota_fecp, "credito_icms": credito_icms,
        }
        cols = list(texto) + list(numeros) + ["beneficio_id"]
        vals = list(texto.values()) + list(numeros.values()) + [beneficio_id]
        with system_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO fiscal_config (produto_id, {', '.join(cols)}) VALUES (?, {', '.join('?' for _ in cols)})"
                f" ON CONFLICT(produto_id) DO UPDATE SET"
                f" {', '.join(f'{c}=COALESCE(excluded.{c}, fiscal_config.{c})' for c in cols)}",
                [produto_id] + vals,
            )
            return cur.lastrowid if cur.lastrowid else produto_id

    def list(self, page: int = 0, limit: int = 100, termo: str | None = None) -> list[dict]:
        sql = (
            "SELECT f.*, p.sku, p.preco, p.nome AS produto_nome, p.marca,"
            " cat.nome AS categoria"
            " FROM fiscal_config f"
            " JOIN produtos_cadastro p ON p.id = f.produto_id"
            " LEFT JOIN categorias cat ON cat.id = p.categoria_id"
        )
        args: list = []
        if termo:
            sql += " WHERE (p.nome LIKE ? OR p.sku LIKE ? OR f.ncm LIKE ?)"
            like = f"%{termo}%"
            args.extend([like, like, like])
        sql += " ORDER BY p.nome, p.sku LIMIT ? OFFSET ?"
        args.extend([limit, page * limit])
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def gerar_config_padrao(self, cfop_padrao: str = "5.102", cst_icms: str = "00") -> int:
        with system_conn() as conn:
            existentes = {r["produto_id"] for r in conn.execute(
                "SELECT produto_id FROM fiscal_config"
            ).fetchall()}
            variantes = conn.execute("SELECT id, ncm FROM produtos_cadastro").fetchall()
            count = 0
            for v in variantes:
                if v["id"] in existentes:
                    continue
                conn.execute(
                    "INSERT INTO fiscal_config (produto_id, ncm, cfop, cst_icms, cst_pis, cst_cofins,"
                    " aliquota_icms, aliquota_pis, aliquota_cofins)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (v["id"], v["ncm"] or "", cfop_padrao, cst_icms, "01", "01", 18, 1.65, 7.6),
                )
                count += 1
            return count

    # ------------------------------------------------------------------

    def registrar_historico_config(self, produto_id: int, tipo: str, usuario_id: int | None = None) -> int:
        """Snapshot atual da fiscal_config em fiscal_config_historico (auditoria)."""
        with system_conn() as conn:
            cfg = conn.execute(
                "SELECT * FROM fiscal_config WHERE produto_id=?", (produto_id,)
            ).fetchone()
            if cfg is None:
                return 0
            cols = (
                "ncm, cfop, cst_icms, cst_pis, cst_cofins, aliquota_icms, aliquota_pis,"
                " aliquota_cofins, aliquota_ipi, origem, cest, csosn, aliquota_icms_st, mva,"
                " base_reducao, aliquota_interestadual, aliquota_fecp, credito_icms,"
                " beneficio_id, vigencia_inicio, vigencia_fim"
            )
            cur = conn.execute(
                f"INSERT INTO fiscal_config_historico"
                f" (produto_id, tipo, {cols}, usuario_id)"
                f" VALUES (?,?,{', '.join('?' for _ in cols.split(','))},?)",
                [produto_id, tipo] + [cfg[c.strip()] for c in cols.split(",")] + [usuario_id],
            )
            return cur.lastrowid

    def list_historico(self, termo: str | None = None, produto_id: int | None = None, limit: int = 200) -> list[dict]:
        sql = (
            "SELECT h.*, p.sku, p.nome AS produto_nome, p.marca, u.nome AS usuario_nome"
            " FROM fiscal_config_historico h"
            " JOIN produtos_cadastro p ON p.id = h.produto_id"
            " LEFT JOIN usuarios u ON u.id = h.usuario_id"
        )
        conds, args = [], []
        if produto_id:
            conds.append("h.produto_id=?")
            args.append(produto_id)
        if termo:
            like = f"%{termo}%"
            conds.append("(p.nome LIKE ? OR p.sku LIKE ? OR h.ncm LIKE ?)")
            args += [like, like, like]
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY h.id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


cfop_repo = CfopRepository()
cst_repo = CstRepository()
fiscal_config_repo = FiscalConfigRepository()


class CestRepository:

    def list(self, ncm: str | None = None, somente_ativos: bool = True) -> list[dict]:
        sql = "SELECT * FROM cest"
        conds, args = [], []
        if somente_ativos:
            conds.append("ativo=1")
        if ncm:
            conds.append("ncm_prefix LIKE ?")
            args.append(ncm[:4] + "%")
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY codigo"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


class CsosnRepository:

    def list(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM csosn ORDER BY codigo").fetchall()]


class BeneficioFiscalRepository:

    def list(self, somente_ativos: bool = True) -> list[dict]:
        sql = "SELECT * FROM beneficios_fiscais"
        if somente_ativos:
            sql += " WHERE ativo=1"
        sql += " ORDER BY descricao"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]


cest_repo = CestRepository()
csosn_repo = CsosnRepository()
beneficio_fiscal_repo = BeneficioFiscalRepository()
