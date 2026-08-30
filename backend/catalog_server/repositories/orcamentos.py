"""Repositório de orçamentos de venda ao cliente (PDV).

Itens são salvos de forma desnormalizada (nome/sku/marca/preço) no momento da
criação — o orçamento permanece estável mesmo se o catálogo mudar depois.
"""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.orcamento_status import (
    STATUS_LIST,
    aplicar_transicao,
    pode_editar_conteudo,
)


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
                   o.desconto_autorizado_em, o.cliente_id, o.condicao_pagamento_id,
                   cp.nome AS condicao_nome,
                   (SELECT COUNT(*) FROM orcamento_itens oi WHERE oi.orcamento_id=o.id) AS n_itens,
                   (SELECT u.nome FROM usuarios u WHERE u.id=o.usuario_id) AS usuario_nome,
                   (SELECT COUNT(*) FROM contas_receber cr
                     WHERE cr.documento=o.numero AND cr.status IN ('aberto','parcial')) AS n_parcelas
            FROM orcamentos o
            LEFT JOIN condicoes_pagamento cp ON cp.id=o.condicao_pagamento_id
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

    def buscar(self, orcamento_id: int, _conn=None) -> dict | None:
        if _conn is None:
            with system_conn() as conn:
                return self.buscar(orcamento_id, _conn=conn)

        conn = _conn
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
        with system_conn() as conn:
            row = conn.execute(
                "SELECT status FROM orcamentos WHERE id=?", (orcamento_id,)
            ).fetchone()
            if row is None:
                return False
            status_atual = row["status"]

            # Status (transição) é gerenciado pelo módulo de lifecycle.
            if status is not None:
                if status != status_atual:
                    conn.commit()
                    return aplicar_transicao(orcamento_id, status)
                status = None

            # Conteúdo: só editável até `liberado`.
            conteudo_mudou = any(
                val is not None
                for val in (cliente, contato, validade_dias, observacoes, desconto, condicao_pagamento_id)
            )
            if conteudo_mudou and not pode_editar_conteudo(status_atual):
                raise PermissionError(
                    f"Orçamento {status_atual}: edição de conteúdo bloqueada (edite até liberado)"
                )

            fields, params = [], []
            for key, val in (
                ("cliente", cliente),
                ("contato", contato),
                ("validade_dias", validade_dias),
                ("observacoes", observacoes),
                ("desconto", desconto),
                ("condicao_pagamento_id", condicao_pagamento_id),
            ):
                if val is not None:
                    fields.append(f"{key}=?")
                    params.append(val)
            if not fields:
                return False
            params.append(orcamento_id)
            cur = conn.execute(
                f"UPDATE orcamentos SET {', '.join(fields)} WHERE id=?",
                params,
            )
            if cur.rowcount == 0:
                return False
            self._recalc_totals(conn, orcamento_id)
            # Qualquer alteração de conteúdo invalida uma autorização de alçada
            # anterior (o desconto efetivo pode ter mudado). Roda DEPOIS do
            # UPDATE para recalcular com o novo desconto: dentro da alçada →
            # `ok` (sem nova aprovação); acima → `pendente`.
            self._revogar_aprovacao(conn, orcamento_id, "conteúdo editado")
            conn.execute(
                "UPDATE orcamentos SET atualizado_em=datetime('now') WHERE id=?",
                (orcamento_id,),
            )
            conn.commit()
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
                "SELECT status FROM orcamentos WHERE id=?", (orcamento_id,)
            ).fetchone()
            if cur is None:
                return False
            status_atual = cur["status"]
            if not pode_editar_conteudo(status_atual):
                raise PermissionError(
                    f"Orçamento {status_atual}: edição de conteúdo bloqueada (edite até liberado)"
                )
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
            self._revogar_aprovacao(conn, orcamento_id, "itens alterados")
            conn.execute(
                "UPDATE orcamentos SET atualizado_em=datetime('now') WHERE id=?",
                (orcamento_id,),
            )
            conn.commit()
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
                "UPDATE orcamentos SET desconto_autorizado=1, desconto_status='aprovado',"
                " desconto_autorizado_por=?, desconto_autorizado_em=datetime('now')"
                " WHERE id=? AND desconto_autorizado=0",
                (usuario_id, orcamento_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def rejeitar_desconto(self, orcamento_id: int, usuario_id: int, motivo: str) -> bool:
        """Registra a rejeição de desconto (motivo obrigatório)."""
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE orcamentos SET desconto_status='rejeitado',"
                " desconto_rejeitado_por=?, desconto_rejeitado_em=now(),"
                " desconto_rejeitado_motivo=?"
                " WHERE id=?",
                (usuario_id, motivo.strip(), orcamento_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def _revogar_aprovacao(self, conn, orcamento_id: int, motivo: str) -> None:
        """Revoga a autorização de desconto após edição de conteúdo.

        Zera os campos legados e recalcula `desconto_status`: se o novo desconto
        efetivo estiver dentro da alçada do vendedor vira `ok` (sem nova
        aprovação); se estiver acima, vira `pendente` (exige nova autorização).
        Grava log de auditoria.
        """
        # Resumo do desconto a partir da própria conexão (evita abrir outra).
        base = sum(
            float(it.get("preco_unitario") or 0) * float(it.get("quantidade") or 0)
            for it in (self._itens_do_conn(conn, orcamento_id) or [])
        )
        liquido = sum(
            float(it.get("subtotal") or 0)
            for it in (self._itens_do_conn(conn, orcamento_id) or [])
        )
        cab = conn.execute(
            "SELECT desconto FROM orcamentos WHERE id=?", (orcamento_id,)
        ).fetchone()
        desconto = float(cab["desconto"] or 0) if cab else 0.0
        desconto_total = max(0.0, base - liquido + desconto)
        desconto_pct = (desconto_total / base * 100.0) if base > 0 else 0.0

        usuario_id = conn.execute(
            "SELECT usuario_id FROM orcamentos WHERE id=?", (orcamento_id,)
        ).fetchone()
        solicitante = usuario_id["usuario_id"] if usuario_id else None

        if desconto_pct <= 0.01:
            novo_status = "ok"
        else:
            from catalog_server.repositories.usuarios import usuario_repo

            user = usuario_repo.get(solicitante) if solicitante else None
            limite = float(user.get("desconto_limite_pct") or 0) if user else 0.0
            novo_status = "ok" if desconto_pct <= limite + 1e-6 else "pendente"

        conn.execute(
            "UPDATE orcamentos SET desconto_status=?, desconto_autorizado=0,"
            " desconto_autorizado_por=NULL, desconto_autorizado_em=NULL,"
            " desconto_rejeitado_por=NULL, desconto_rejeitado_em=NULL,"
            " desconto_rejeitado_motivo='' WHERE id=?",
            (novo_status, orcamento_id),
        )
        conn.execute(
            "INSERT INTO desconto_aprovacao_log"
            " (orcamento_id, solicitante_id, desconto_pct, status, motivo)"
            " VALUES (?,?,?,?,?)",
            (orcamento_id, solicitante, round(desconto_pct, 2), "revogado", motivo),
        )

    @staticmethod
    def _itens_do_conn(conn, orcamento_id: int) -> list[dict]:
        rows = conn.execute(
            "SELECT preco_unitario, quantidade, subtotal FROM orcamento_itens"
            " WHERE orcamento_id=?",
            (orcamento_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------

    def pendentes_aprovacao(self, aprovador_id: int) -> list[dict]:
        """Fila do aprovador: orçamentos/pedidos com desconto pendente (acima da
        alçada do vendedor) e dentro da alçada do aprovador."""
        from catalog_server.repositories.usuarios import usuario_repo

        aprovador = usuario_repo.get(aprovador_id)
        limite_aprovador = float(aprovador.get("desconto_limite_pct") or 0) if aprovador else 0.0
        with system_conn() as conn:
            rows = conn.execute(
                """
                SELECT o.id, o.numero, o.cliente, o.total, o.desconto_status,
                       o.usuario_id, o.desconto_autorizado_por, o.virou_pedido
                FROM orcamentos o
                WHERE o.desconto_status = 'pendente'
                  AND (o.usuario_id IS NULL OR o.usuario_id <> ?)
                ORDER BY o.id
                """,
                (aprovador_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["desconto_pct"] = 0.0
            d["limite_aprovador"] = limite_aprovador
            out.append(d)
        return out

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
