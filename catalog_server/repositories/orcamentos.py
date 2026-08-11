"""Repositório de orçamentos de venda ao cliente (PDV).

Itens são salvos de forma desnormalizada (nome/sku/marca/preço) no momento da
criação — o orçamento permanece estável mesmo se o catálogo mudar depois.
"""
from __future__ import annotations

from catalog_server.db import system_conn

STATUS_LIST = ("rascunho", "ativo", "em_analise", "liberado", "faturado", "cancelado")


def next_numero(conn) -> str:
    row = conn.execute("SELECT COALESCE(MAX(id), 0) AS n FROM orcamentos").fetchone()
    return f"ORC{row['n'] + 1:04d}"


def _calc_item(preco: float, quantidade: float, desconto: float) -> float:
    return max(0.0, preco * quantidade * (1 - (desconto / 100.0)))


class OrcamentoRepository:

    # ------------------------------------------------------------------

    def criar(
        self,
        cliente: str,
        contato: str = "",
        validade_dias: int = 7,
        observacoes: str = "",
        desconto: float = 0.0,
        itens: list[dict] | None = None,
        frete: float = 0.0,
        seguro: float = 0.0,
        despesas_acessorias: float = 0.0,
        status: str = "rascunho",
        condicao_pagamento_id: int | None = None,
    ) -> tuple[int, str]:
        """Cria o orçamento com seus itens e calcula subtotal/total."""
        itens = itens or []
        with system_conn() as conn:
            numero = next_numero(conn)
            subtotal = 0.0
            for it in itens:
                subtotal += _calc_item(
                    float(it.get("preco_unitario") or 0),
                    float(it.get("quantidade") or 1),
                    float(it.get("desconto_percentual") or 0),
                )
            desconto = max(0.0, float(desconto or 0))
            frete = max(0.0, float(frete or 0))
            seguro = max(0.0, float(seguro or 0))
            desp = max(0.0, float(despesas_acessorias or 0))
            total = max(0.0, subtotal - desconto + frete + seguro + desp)
            if status not in STATUS_LIST:
                status = "rascunho"
            cur = conn.execute(
                f"""
                INSERT INTO orcamentos
                    (numero, cliente, contato, validade_dias, observacoes,
                     status, desconto, subtotal, total,
                     frete, seguro, despesas_acessorias,
                     total_liquido, condicao_pagamento_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    numero,
                    (cliente or "").strip(),
                    (contato or "").strip(),
                    int(validade_dias or 7),
                    (observacoes or "").strip(),
                    status,
                    desconto,
                    subtotal,
                    total,
                    frete,
                    seguro,
                    desp,
                    total,
                    condicao_pagamento_id,
                ),
            )
            orcamento_id = cur.lastrowid
            for it in itens:
                conn.execute(
                    """
                    INSERT INTO orcamento_itens
                        (orcamento_id, produto_id, nome, sku, marca, especificacao,
                         quantidade, preco_unitario, desconto_percentual, subtotal)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        orcamento_id,
                        it.get("produto_id"),
                        (it.get("nome") or "").strip(),
                        (it.get("sku") or "").strip(),
                        (it.get("marca") or "").strip(),
                        (it.get("especificacao") or "").strip(),
                        float(it.get("quantidade") or 1),
                        float(it.get("preco_unitario") or 0),
                        float(it.get("desconto_percentual") or 0),
                        _calc_item(
                            float(it.get("preco_unitario") or 0),
                            float(it.get("quantidade") or 1),
                            float(it.get("desconto_percentual") or 0),
                        ),
                    ),
                )
            return orcamento_id, numero

    # ------------------------------------------------------------------

    def listar(self, status: str = "") -> list[dict]:
        sql = """
            SELECT o.id, o.numero, o.cliente, o.contato, o.status, o.desconto,
                   o.subtotal, o.total, o.validade_dias, o.criado_em, o.observacoes,
                   (SELECT COUNT(*) FROM orcamento_itens oi WHERE oi.orcamento_id=o.id) AS n_itens
            FROM orcamentos o
        """
        params: list = []
        if status and status in STATUS_LIST:
            sql += " WHERE o.status=?"
            params.append(status)
        sql += " ORDER BY o.id DESC"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    # ------------------------------------------------------------------

    def buscar(self, orcamento_id: int) -> dict | None:
        with system_conn() as conn:
            cab = conn.execute(
                "SELECT * FROM orcamentos WHERE id=?", (orcamento_id,)
            ).fetchone()
            if cab is None:
                return None
            itens = conn.execute(
                "SELECT * FROM orcamento_itens WHERE orcamento_id=? ORDER BY id",
                (orcamento_id,),
            ).fetchall()
            return {**dict(cab), "itens": [dict(r) for r in itens]}

    # ------------------------------------------------------------------

    def atualizar_cabecalho(
        self,
        orcamento_id: int,
        cliente: str | None = None,
        contato: str | None = None,
        validade_dias: int | None = None,
        observacoes: str | None = None,
        status: str | None = None,
        desconto: float | None = None,
    ) -> bool:
        fields, params = [], []
        for key, val in (
            ("cliente", cliente),
            ("contato", contato),
            ("validade_dias", validade_dias),
            ("observacoes", observacoes),
            ("status", status),
            ("desconto", desconto),
        ):
            if val is not None:
                fields.append(f"{key}=?")
                params.append(val)
        if not fields:
            return False
        params.append(orcamento_id)
        with system_conn() as conn:
            cur = conn.execute(
                f"UPDATE orcamentos SET {', '.join(fields)} WHERE id=?",
                params,
            )
            if cur.rowcount == 0:
                return False
            self._recalc_totals(conn, orcamento_id)
            conn.execute(
                "UPDATE orcamentos SET atualizado_em=datetime('now') WHERE id=?",
                (orcamento_id,),
            )
        return True

    # ------------------------------------------------------------------

    def substituir_itens(self, orcamento_id: int, itens: list[dict]) -> bool:
        """Substitui integralmente os itens do orçamento e recalcula totais."""
        with system_conn() as conn:
            cur = conn.execute(
                "SELECT 1 FROM orcamentos WHERE id=?", (orcamento_id,)
            ).fetchone()
            if cur is None:
                return False
            conn.execute("DELETE FROM orcamento_itens WHERE orcamento_id=?", (orcamento_id,))
            for it in itens:
                conn.execute(
                    """
                    INSERT INTO orcamento_itens
                        (orcamento_id, produto_id, nome, sku, marca, especificacao,
                         quantidade, preco_unitario, desconto_percentual, subtotal)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        orcamento_id,
                        it.get("produto_id"),
                        (it.get("nome") or "").strip(),
                        (it.get("sku") or "").strip(),
                        (it.get("marca") or "").strip(),
                        (it.get("especificacao") or "").strip(),
                        float(it.get("quantidade") or 1),
                        float(it.get("preco_unitario") or 0),
                        float(it.get("desconto_percentual") or 0),
                        _calc_item(
                            float(it.get("preco_unitario") or 0),
                            float(it.get("quantidade") or 1),
                            float(it.get("desconto_percentual") or 0),
                        ),
                    ),
                )
            self._recalc_totals(conn, orcamento_id)
            conn.execute(
                "UPDATE orcamentos SET atualizado_em=datetime('now') WHERE id=?",
                (orcamento_id,),
            )
        return True

    # ------------------------------------------------------------------

    def excluir(self, orcamento_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute("DELETE FROM orcamentos WHERE id=?", (orcamento_id,))
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def _recalc_totals(self, conn, orcamento_id: int) -> None:
        row = conn.execute(
            "SELECT COALESCE(SUM(subtotal),0) AS s FROM orcamento_itens WHERE orcamento_id=?",
            (orcamento_id,),
        ).fetchone()
        subtotal = float(row["s"] or 0)
        cab = conn.execute(
            "SELECT desconto FROM orcamentos WHERE id=?", (orcamento_id,)
        ).fetchone()
        desconto = max(0.0, float(cab["desconto"] or 0))
        conn.execute(
            "UPDATE orcamentos SET subtotal=?, total=? WHERE id=?",
            (subtotal, max(0.0, subtotal - desconto), orcamento_id),
        )


# Alias para uso nos blueprints.
orcamento_repo = OrcamentoRepository()