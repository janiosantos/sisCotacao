from __future__ import annotations

from catalog_server.db import system_conn


class FornecedorPrecoRepository:

    def list(self, fornecedor_id: int | None = None, produto_id: int | None = None) -> list[dict]:
        sql = (
            "SELECT f.*, p.sku, p.nome AS produto_nome, fn.nome AS fornecedor_nome"
            " FROM fornecedor_preco f"
            " JOIN produtos_cadastro p ON p.id = f.produto_id"
            " JOIN fornecedores fn ON fn.id = f.fornecedor_id WHERE 1=1"
        )
        args: list = []
        if fornecedor_id:
            sql += " AND f.fornecedor_id = ?"; args.append(fornecedor_id)
        if produto_id:
            sql += " AND f.produto_id = ?"; args.append(produto_id)
        sql += " ORDER BY p.nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert(self, fornecedor_id: int, produto_id: int, preco: float, prazo: int | None = None, icms: float = 0, ipi: float = 0) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fornecedor_preco (fornecedor_id, produto_id, preco, prazo_entrega, icms, ipi)"
                " VALUES (?,?,?,?,?,?) ON CONFLICT(fornecedor_id, produto_id) DO UPDATE SET"
                " preco=excluded.preco, prazo_entrega=excluded.prazo_entrega, icms=excluded.icms, ipi=excluded.ipi",
                (fornecedor_id, produto_id, preco, prazo, icms, ipi),
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

    def get(self, sc_id: int) -> dict | None:
        """Solicitação com seus itens (variante + produto)."""
        with system_conn() as conn:
            row = conn.execute(
                "SELECT s.*, u.nome AS usuario_nome FROM solicitacao_compra s"
                " LEFT JOIN usuarios u ON u.id=s.usuario_id WHERE s.id=?",
                (sc_id,),
            ).fetchone()
            if row is None:
                return None
            itens = conn.execute(
                """SELECT si.*, p.sku, p.unidade_venda, p.nome AS produto_nome
                   FROM solicitacao_itens si
                   JOIN produtos_cadastro p ON p.id=si.produto_id
                   WHERE si.solicitacao_id=? ORDER BY si.id""",
                (sc_id,),
            ).fetchall()
            d = dict(row)
            d["itens"] = [dict(r) for r in itens]
            return d

    def create(self, codigo: str, descricao: str = "", observacao: str = "", usuario_id: int | None = None,
               prioridade: str = "media", origem: str = "manual", centro_custo: str | None = None,
               deposito_id: int | None = None, prazo_desejado: str | None = None) -> int:
        prioridade = (prioridade or "media").strip().lower()
        if prioridade not in ("baixa", "media", "alta", "urgente"):
            raise ValueError("prioridade inválida")
        origem = (origem or "manual").strip().lower()
        if origem not in ("manual", "sugestao", "obra", "projeto"):
            raise ValueError("origem inválida")
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO solicitacao_compra (codigo, descricao, observacao, usuario_id,"
                " prioridade, origem, centro_custo, deposito_id, prazo_desejado)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (codigo.strip(), descricao.strip(), observacao.strip(), usuario_id,
                 prioridade, origem, (centro_custo or "").strip() or None, deposito_id, prazo_desejado),
            ).lastrowid

    # ── Máquina de estados (COM-007) ──────────────────────────
    _TRANSICOES: dict[str, set[str]] = {
        "rascunho": {"enviada", "cancelada"},
        "enviada": {"aprovada", "cancelada"},
        "aprovada": {"cotando"},
        "cotando": {"convertida"},
        "convertida": set(),
        "cancelada": set(),
    }
    _EDITAVEIS = {"rascunho", "enviada"}

    def transicionar(self, sc_id: int, novo_status: str, usuario_id: int | None = None) -> dict:
        novo_status = (novo_status or "").strip().lower()
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM solicitacao_compra WHERE id=?", (sc_id,)).fetchone()
            if not row:
                raise LookupError("Solicitação não encontrada")
            atual = row["status"]
            if novo_status not in self._TRANSICOES.get(atual, set()):
                raise ValueError(f"Transição inválida: {atual} → {novo_status}")
            if novo_status == "enviada":
                conn.execute("UPDATE solicitacao_compra SET status='enviada', data_enviada=NOW() WHERE id=?", (sc_id,))
            elif novo_status == "aprovada":
                if usuario_id is not None and row["usuario_id"] == usuario_id:
                    raise ValueError("Aprovador não pode ser o próprio solicitante")
                conn.execute(
                    "UPDATE solicitacao_compra SET status='aprovada', data_aprovacao=NOW(), aprovador_id=? WHERE id=?",
                    (usuario_id, sc_id),
                )
            else:
                conn.execute("UPDATE solicitacao_compra SET status=? WHERE id=?", (novo_status, sc_id))
            return {"id": sc_id, "de": atual, "para": novo_status}

    def _garantir_editavel(self, conn, sc_id: int) -> None:
        row = conn.execute("SELECT status FROM solicitacao_compra WHERE id=?", (sc_id,)).fetchone()
        if not row:
            raise LookupError("Solicitação não encontrada")
        if row["status"] not in self._EDITAVEIS:
            raise ValueError(f"Solicitação {row['status']} não pode ser editada sem nova versão")

    def aprovar(self, sc_id: int, aprovador_id: int, status: str = "aprovada") -> bool:
        return self.transicionar(sc_id, status, aprovador_id).get("para") == status

    def add_item(self, sc_id: int, produto_id: int, quantidade: float, justificativa: str = "",
                 unidade: str = "UN", necessidade: float | None = None, origem_sugestao: str | None = None) -> int:
        with system_conn() as conn:
            self._garantir_editavel(conn, sc_id)
            return conn.execute(
                "INSERT INTO solicitacao_itens (solicitacao_id, produto_id, quantidade, justificativa,"
                " unidade, necessidade, origem_sugestao) VALUES (?,?,?,?,?,?,?)",
                (sc_id, produto_id, quantidade, justificativa.strip(),
                 (unidade or "UN").strip().upper(), necessidade, origem_sugestao),
            ).lastrowid

    def remover_item(self, sc_id: int, item_id: int) -> bool:
        with system_conn() as conn:
            self._garantir_editavel(conn, sc_id)
            cur = conn.execute(
                "DELETE FROM solicitacao_itens WHERE id=? AND solicitacao_id=?",
                (item_id, sc_id),
            )
            return cur.rowcount > 0


fornecedor_preco_repo = FornecedorPrecoRepository()
solicitacao_repo = SolicitacaoRepository()


class FornecedorPreferencialRepository:

    def list(self, produto_id: int | None = None) -> list[dict]:
        sql = (
            "SELECT f.*, fn.nome AS fornecedor_nome, p.sku, p.nome AS produto_nome"
            " FROM fornecedor_preferencial f"
            " JOIN fornecedores fn ON fn.id = f.fornecedor_id"
            " JOIN produtos_cadastro p ON p.id = f.produto_id"
        )
        args: list = []
        if produto_id:
            sql += " WHERE f.produto_id = ?"; args.append(produto_id)
        sql += " ORDER BY f.ranking, fn.nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def upsert(self, produto_id: int, fornecedor_id: int, ranking: int = 1, preco: float | None = None, prazo: int | None = None) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking, ultimo_preco, ultimo_prazo)"
                " VALUES (?,?,?,?,?) ON CONFLICT(produto_id, fornecedor_id) DO UPDATE SET"
                " ranking=excluded.ranking, ultimo_preco=excluded.ultimo_preco, ultimo_prazo=excluded.ultimo_prazo",
                (produto_id, fornecedor_id, ranking, preco, prazo),
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

    def upsert(
        self,
        ncm: str,
        descricao: str = "",
        aliquota_federal: float = 0,
        aliquota_estadual: float = 0,
        aliquota_municipal: float = 0,
        fonte: str = "",
        vigencia_inicio: str | None = None,
        vigencia_fim: str | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO ibpt (ncm, descricao, aliquota_federal, aliquota_estadual, aliquota_municipal,"
                " fonte, vigencia_inicio, vigencia_fim)"
                " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(ncm) DO UPDATE SET"
                " descricao=excluded.descricao, aliquota_federal=excluded.aliquota_federal,"
                " aliquota_estadual=excluded.aliquota_estadual, aliquota_municipal=excluded.aliquota_municipal,"
                " fonte=excluded.fonte, vigencia_inicio=excluded.vigencia_inicio, vigencia_fim=excluded.vigencia_fim",
                (ncm.strip(), descricao.strip(), aliquota_federal, aliquota_estadual, aliquota_municipal,
                 fonte.strip(), vigencia_inicio, vigencia_fim),
            )
            return cur.lastrowid

    def list_sugestoes(
        self,
        status: str | None = None,
        q: str | None = None,
        confianca_min: float | None = None,
        limit: int = 200,
    ) -> list[dict]:
        sql = (
            "SELECT s.*, p.sku, p.nome AS produto_nome, p.marca"
            " FROM ibpt_sugestoes s"
            " JOIN produtos_cadastro p ON p.id = s.produto_id"
        )
        conds, args = [], []
        if status and status in ("pendente", "aplicada", "rejeitada"):
            conds.append("s.status=?")
            args.append(status)
        if q:
            like = f"%{q}%"
            conds.append("(p.nome LIKE ? OR p.sku LIKE ? OR s.ncm LIKE ?)")
            args += [like, like, like]
        if confianca_min is not None:
            conds.append("s.confianca >= ?")
            args.append(confianca_min)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY s.confianca DESC, p.nome LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def set_sugestao_status(self, sugestao_id: int, status: str) -> bool:
        if status not in ("aplicada", "rejeitada"):
            return False
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE ibpt_sugestoes SET status=?, aplicado_em=datetime('now')"
                " WHERE id=? AND status='pendente'",
                (status, sugestao_id),
            )
            return cur.rowcount > 0


fornecedor_preferencial_repo = FornecedorPreferencialRepository()
tolerancia_repo = ToleranciaRepository()

ibpt_repo = IbptRepository()
