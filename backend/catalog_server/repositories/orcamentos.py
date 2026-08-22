"""Repositório de orçamentos de venda ao cliente (PDV).

Itens são salvos de forma desnormalizada (nome/sku/marca/preço) no momento da
criação — o orçamento permanece estável mesmo se o catálogo mudar depois.
"""
from __future__ import annotations

from catalog_server.db import system_conn

STATUS_LIST = ("rascunho", "ativo", "em_analise", "liberado", "faturado", "recebido", "cancelado")


def next_numero(conn) -> str:
    row = conn.execute("SELECT COALESCE(MAX(id), 0) AS n FROM orcamentos").fetchone()
    return f"ORC{row['n'] + 1:04d}"


def _calc_item(preco: float, quantidade: float, desconto: float) -> float:
    return max(0.0, preco * quantidade * (1 - (desconto / 100.0)))


def resumo_desconto(orc: dict) -> dict:
    """Calcula o desconto total do orçamento (itens + desconto geral).

    Retorna a base (soma dos preços cheios), o total descontado em R$ e o
    percentual sobre a base.
    """
    base = sum(
        float(it.get("preco_unitario") or 0) * float(it.get("quantidade") or 0)
        for it in (orc.get("itens") or [])
    )
    itens_liquido = sum(
        float(it.get("subtotal") or 0)
        for it in (orc.get("itens") or [])
    )
    desconto_total = max(0.0, base - itens_liquido + float(orc.get("desconto") or 0))
    pct = (desconto_total / base * 100.0) if base > 0 else 0.0
    return {
        "base": round(base, 2),
        "desconto_total": round(desconto_total, 2),
        "desconto_pct": round(pct, 2),
    }


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
        usuario_id: int | None = None,
        cliente_id: int | None = None,
        cliente_doc: str | None = None,
        uf_destino: str | None = None,
        tipo_cliente: str | None = None,
        contribuinte: str | None = None,
        ie: str | None = None,
        modelo_documento: str | None = None,
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
                     total_liquido, condicao_pagamento_id, usuario_id,
                     cliente_id, cliente_doc, uf_destino, tipo_cliente,
                     contribuinte, ie, modelo_documento)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                    usuario_id,
                    cliente_id,
                    cliente_doc,
                    (uf_destino or "").strip().upper() or None,
                    tipo_cliente,
                    contribuinte,
                    ie,
                    modelo_documento,
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

    def listar(
        self,
        status: str = "",
        usuario_id: int | None = None,
        q: str = "",
        data_inicio: str | None = None,
        data_fim: str | None = None,
    ) -> list[dict]:
        sql = """
            SELECT o.id, o.numero, o.cliente, o.contato, o.status, o.desconto,
                   o.subtotal, o.total, o.validade_dias, o.criado_em, o.observacoes,
                   o.usuario_id, o.desconto_autorizado, o.desconto_autorizado_por,
                   o.desconto_autorizado_em,
                   (SELECT COUNT(*) FROM orcamento_itens oi WHERE oi.orcamento_id=o.id) AS n_itens,
                   (SELECT u.nome FROM usuarios u WHERE u.id=o.usuario_id) AS usuario_nome
            FROM orcamentos o
        """
        params: list = []
        conds: list = []
        if status and status in STATUS_LIST:
            conds.append("o.status=?")
            params.append(status)
        if usuario_id is not None:
            conds.append("o.usuario_id=?")
            params.append(usuario_id)
        if q:
            like = f"%{q}%"
            conds.append("(o.numero LIKE ? OR o.cliente LIKE ?)")
            params.extend([like, like])
        if data_inicio:
            conds.append("date(o.criado_em) >= ?")
            params.append(data_inicio)
        if data_fim:
            conds.append("date(o.criado_em) <= ?")
            params.append(data_fim)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
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
            d = {**dict(cab), "itens": [dict(r) for r in itens]}
            if d.get("desconto_autorizado_por"):
                u = conn.execute(
                    "SELECT nome FROM usuarios WHERE id=?",
                    (d["desconto_autorizado_por"],),
                ).fetchone()
                d["desconto_autorizado_nome"] = (u["nome"] if u else None)
            else:
                d["desconto_autorizado_nome"] = None
            return d

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
        condicao_pagamento_id: int | None = None,
    ) -> bool:
        fields, params = [], []
        for key, val in (
            ("cliente", cliente),
            ("contato", contato),
            ("validade_dias", validade_dias),
            ("observacoes", observacoes),
            ("status", status),
            ("desconto", desconto),
            ("condicao_pagamento_id", condicao_pagamento_id),
        ):
            if val is not None:
                fields.append(f"{key}=?")
                params.append(val)
        if not fields:
            return False
        # O desconto mudou: uma autorização de alçada anterior valia para o
        # percentual de ANTES da edição. Zera para forçar reavaliação — se o
        # novo desconto já estiver dentro do limite do vendedor, a checagem
        # de alçada simplesmente não vai exigir nada de novo.
        if desconto is not None:
            fields.append("desconto_autorizado=0")
            fields.append("desconto_autorizado_por=NULL")
            fields.append("desconto_autorizado_em=NULL")
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
        """Substitui integralmente os itens do orçamento e recalcula totais.

        Também zera uma autorização de desconto pré-existente: o percentual
        efetivo depende dos itens (desconto por item entra na conta), então
        trocar os itens invalida a autorização anterior pelo mesmo motivo
        que trocar o desconto geral invalida — ver `atualizar_cabecalho`.
        """
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
                "UPDATE orcamentos SET atualizado_em=datetime('now'),"
                " desconto_autorizado=0, desconto_autorizado_por=NULL,"
                " desconto_autorizado_em=NULL WHERE id=?",
                (orcamento_id,),
            )
        return True

    # ------------------------------------------------------------------

    def excluir(self, orcamento_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute("DELETE FROM orcamentos WHERE id=?", (orcamento_id,))
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def autorizar_desconto(self, orcamento_id: int, usuario_id: int) -> bool:
        """Registra a aprovação de desconto acima da alçada do vendedor."""
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE orcamentos SET desconto_autorizado=1,"
                " desconto_autorizado_por=?, desconto_autorizado_em=datetime('now')"
                " WHERE id=? AND desconto_autorizado=0",
                (usuario_id, orcamento_id),
            )
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