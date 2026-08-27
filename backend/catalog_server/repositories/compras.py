"""Repositório do fluxo de compra em tela única (NFC).

Agrega o ciclo: montar lista -> convidar fornecedores (token/link) -> portal
de preenchimento do fornecedor -> matriz de comparação -> pedidos de compra.
"""
from __future__ import annotations

import secrets

from catalog_server.db import next_cotacao_numero, system_conn


def _novo_token() -> str:
    return secrets.token_urlsafe(12)


class ComprasRepository:

    # ------------------------------------------------------------------
    # Criação da cotação (etapa 1 e 2 combinadas)
    # ------------------------------------------------------------------

    def create_rfq(
        self,
        apelido: str,
        data_limite: str,
        cliente: str,
        itens: list[dict],
        fornecedores: list[dict],
    ) -> tuple[int, str]:
        """Cria a cotação (status 'pendente'), seus itens e convida os
        fornecedores, criando os expressos quando necessário."""
        with system_conn() as conn:
            numero = next_cotacao_numero(conn)
            cur = conn.execute(
                "INSERT INTO cotacoes (numero, titulo, cliente, status, data_limite_retorno)"
                " VALUES (?,?,?,'pendente',?)",
                (numero, apelido or None, cliente or None, data_limite or None),
            )
            cotacao_id = cur.lastrowid
            for i in itens:
                vid = int(i["produto_id"])
                unidade = conn.execute(
                    "SELECT unidade_venda FROM produtos_cadastro WHERE id=?", (vid,)
                ).fetchone()
                conn.execute(
                    "INSERT OR IGNORE INTO cotacao_itens (cotacao_id, produto_id, quantidade, unidade_solicitada)"
                    " VALUES (?,?,?,?)",
                    (cotacao_id, vid, float(i.get("quantidade", 1) or 1),
                     (unidade["unidade_venda"] if unidade and unidade["unidade_venda"] else "") or ""),
                )
            for f in fornecedores:
                fid = f.get("fornecedor_id")
                if not fid:
                    fid = self._inserir_fornecedor_express(conn, f)
                conn.execute(
                    "INSERT OR IGNORE INTO cotacao_fornecedores (cotacao_id, fornecedor_id, token)"
                    " VALUES (?,?,?)",
                    (cotacao_id, fid, _novo_token()),
                )
            return cotacao_id, numero

    # ------------------------------------------------------------------

    def _inserir_fornecedor_express(self, conn, f: dict) -> int:
        nome = (f.get("nome") or "").strip()
        if not nome:
            raise ValueError("Fornecedor sem nome")
        cur = conn.execute(
            "INSERT INTO fornecedores (nome, whatsapp, email, representante, ativo)"
            " VALUES (?,?,?,?,1)",
            (nome, (f.get("whatsapp") or "").strip() or None,
             (f.get("email") or "").strip() or None,
             (f.get("representante") or "").strip() or None),
        )
        return cur.lastrowid

    # ------------------------------------------------------------------

    def ensure_tokens(self, cotacao_id: int) -> None:
        """Garante token para todos os fornecedores convidados sem token."""
        with system_conn() as conn:
            rows = conn.execute(
                "SELECT id FROM cotacao_fornecedores WHERE cotacao_id=? AND token IS NULL",
                (cotacao_id,),
            ).fetchall()
            for r in rows:
                conn.execute(
                    "UPDATE cotacao_fornecedores SET token=? WHERE id=?",
                    (_novo_token(), r["id"]),
                )

    # ------------------------------------------------------------------
    # Links/convites
    # ------------------------------------------------------------------

    def get_invites(self, cotacao_id: int) -> list[dict]:
        with system_conn() as conn:
            rows = conn.execute(
                """SELECT cf.id, cf.status, cf.token, cf.data_resposta,
                          f.id AS fornecedor_id, f.nome, f.whatsapp, f.email,
                          f.representante, c.data_limite_retorno
                   FROM cotacao_fornecedores cf
                   JOIN fornecedores f ON f.id = cf.fornecedor_id
                   JOIN cotacoes c ON c.id = cf.cotacao_id
                   WHERE cf.cotacao_id=?
                   ORDER BY f.nome""",
                (cotacao_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------

    def lembrar_invite(self, cotacao_id: int, fornecedor_id: int) -> dict | None:
        """Devolve o convite de um fornecedor (para o 'Lembrar' reenviar).

        Não reenviou nada automaticamente — apenas expõe os dados de contato
        e o link do token para o comprador disparar WhatsApp/e-mail de novo.
        """
        with system_conn() as conn:
            row = conn.execute(
                """SELECT cf.id, cf.status, cf.token, cf.data_resposta,
                          f.id AS fornecedor_id, f.nome, f.whatsapp, f.email,
                          f.representante, c.data_limite_retorno, c.titulo AS apelido
                   FROM cotacao_fornecedores cf
                   JOIN fornecedores f ON f.id = cf.fornecedor_id
                   JOIN cotacoes c ON c.id = cf.cotacao_id
                   WHERE cf.cotacao_id=? AND f.id=?""",
                (cotacao_id, fornecedor_id),
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Portal público do fornecedor (autosserviço)
    # ------------------------------------------------------------------

    def public_portal(self, token: str) -> dict | None:
        """Retorna os dados que o fornecedor vê ao abrir o link (sem login)."""
        with system_conn() as conn:
            row = conn.execute(
                """SELECT cf.token, cf.status, f.id AS fornecedor_id, f.nome,
                          f.representante, c.id AS cotacao_id, c.titulo AS apelido,
                          c.data_limite_retorno, c.observacoes
                   FROM cotacao_fornecedores cf
                   JOIN fornecedores f ON f.id = cf.fornecedor_id
                   JOIN cotacoes c ON c.id = cf.cotacao_id
                   WHERE cf.token=?""",
                (token,),
            ).fetchone()
            if row is None:
                return None
            return dict(row)

    def portal_itens(self, token: str) -> list[dict]:
        with system_conn() as conn:
            rows = conn.execute(
                """SELECT ci.id AS cotacao_item_id, ci.produto_id, ci.quantidade,
                          ci.unidade_solicitada,
                          p.unidade_venda, p.fator_conversao, p.embalagem, p.marca
                   FROM cotacao_fornecedores cf
                   JOIN cotacoes c ON c.id = cf.cotacao_id
                   JOIN cotacao_itens ci ON ci.cotacao_id = c.id
                   LEFT JOIN produtos_cadastro p ON p.id = ci.produto_id
                   WHERE cf.token=? ORDER BY ci.id""",
                (token,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                unidade = d.get("unidade_solicitada") or d.get("unidade_venda") or "UN"
                fator = float(d.get("fator_conversao") or 1) if d.get("fator_conversao") else 1.0
                d["unidade_compra"] = unidade
                d["fator_conversao"] = fator if fator and fator > 0 else 1
                out.append(d)
            return out

    # ------------------------------------------------------------------

    def submit_proposta(
        self,
        token: str,
        precos: list[dict],
        condicao_pagamento: str | None = None,
        condicao_pagamento_dias: int | None = None,
    ) -> bool:
        """Grava os preços enviados pelo fornecedor e atualiza os status.

        `condicao_pagamento` vale para a proposta inteira (não por item):
        é gravada em `cotacao_fornecedores`, junto do status/data_resposta.

        Por item, além do preço, o representante pode informar:
        `unidade_compra`, `fator_conversao`, `marca_ofertada`,
        `motivo_indisponibilidade` e `observacao`.
        """
        with system_conn() as conn:
            row = conn.execute(
                """SELECT cf.id AS cf_id, cf.fornecedor_id, c.id AS cotacao_id
                   FROM cotacao_fornecedores cf
                   JOIN cotacoes c ON c.id = cf.cotacao_id
                   WHERE cf.token=?""",
                (token,),
            ).fetchone()
            if row is None:
                return False
            for p in precos:
                fator = p.get("fator_conversao")
                try:
                    fator = float(fator) if fator not in (None, "") else 1
                except (TypeError, ValueError):
                    fator = 1
                fator = fator if fator and fator > 0 else 1
                disp = p.get("disponibilidade_estoque")
                disp = int(disp) if disp is not None else 1
                motivo = (p.get("motivo_indisponibilidade") or "").strip()
                if disp == 0 and not motivo:
                    motivo = "em_falta_estoque"
                conn.execute(
                    """INSERT INTO cotacao_precos
                         (cotacao_item_id, fornecedor_id, preco_unitario,
                          desconto, prazo_entrega_dias,
                          disponibilidade_estoque, observacao, registrado_em,
                          unidade_compra, fator_conversao, marca_ofertada,
                          motivo_indisponibilidade)
                       VALUES (?,?,?,?,?,?,?, datetime('now'),?,?,?,?)
                       ON CONFLICT(cotacao_item_id, fornecedor_id) DO UPDATE SET
                         preco_unitario=excluded.preco_unitario,
                         desconto=excluded.desconto,
                         prazo_entrega_dias=excluded.prazo_entrega_dias,
                         disponibilidade_estoque=excluded.disponibilidade_estoque,
                         observacao=excluded.observacao,
                         registrado_em=datetime('now'),
                         unidade_compra=excluded.unidade_compra,
                         fator_conversao=excluded.fator_conversao,
                         marca_ofertada=excluded.marca_ofertada,
                         motivo_indisponibilidade=excluded.motivo_indisponibilidade""",
                    (
                        int(p["cotacao_item_id"]),
                        row["fornecedor_id"],
                        float(p.get("preco_unitario") or 0),
                        float(p.get("desconto") if p.get("desconto") is not None else p.get("desconto_percentual") or 0),
                        int(p["prazo_entrega_dias"]) if p.get("prazo_entrega_dias") not in (None, "") else None,
                        disp,
                        (p.get("observacao") or "").strip() or None,
                        (p.get("unidade_compra") or "").strip(),
                        fator,
                        (p.get("marca_ofertada") or "").strip(),
                        motivo,
                    ),
                )
            conn.execute(
                "UPDATE cotacao_fornecedores SET status='respondido',"
                " data_resposta=datetime('now'), condicao_pagamento=?,"
                " condicao_pagamento_dias=? WHERE id=?",
                (
                    (condicao_pagamento or "").strip() or None,
                    condicao_pagamento_dias,
                    row["cf_id"],
                ),
            )
            inv = conn.execute(
                "SELECT COUNT(*) n FROM cotacao_fornecedores WHERE cotacao_id=?",
                (row["cotacao_id"],),
            ).fetchone()["n"]
            resp = conn.execute(
                "SELECT COUNT(*) n FROM cotacao_fornecedores"
                " WHERE cotacao_id=? AND status='respondido'",
                (row["cotacao_id"],),
            ).fetchone()["n"]
            if inv > 0 and resp >= inv:
                conn.execute(
                    "UPDATE cotacoes SET status='analise' WHERE id=?",
                    (row["cotacao_id"],),
                )
            return True

    # ------------------------------------------------------------------
    # Matriz de comparação
    # ------------------------------------------------------------------

    def comparar(self, cotacao_id: int) -> dict | None:
        with system_conn() as conn:
            cot = conn.execute("SELECT * FROM cotacoes WHERE id=?", (cotacao_id,)).fetchone()
            if cot is None:
                return None
            itens = conn.execute(
                "SELECT id AS cotacao_item_id, produto_id, descricao, quantidade"
                " FROM cotacao_itens WHERE cotacao_id=? ORDER BY id",
                (cotacao_id,),
            ).fetchall()
            suppliers = conn.execute(
                """SELECT cf.status AS status, cf.data_resposta,
                          cf.condicao_pagamento, cf.condicao_pagamento_dias,
                          f.id AS fornecedor_id, f.nome
                   FROM cotacao_fornecedores cf JOIN fornecedores f ON f.id=cf.fornecedor_id
                   WHERE cf.cotacao_id=? ORDER BY f.nome""",
                (cotacao_id,),
            ).fetchall()
            precos = conn.execute(
                """SELECT cp.* FROM cotacao_precos cp
                   JOIN cotacao_itens ci ON ci.id=cp.cotacao_item_id
                   WHERE ci.cotacao_id=?""",
                (cotacao_id,),
            ).fetchall()
            return {
                "cotacao": dict(cot),
                "itens": [dict(r) for r in itens],
                "fornecedores": [dict(r) for r in suppliers],
                "precos": [dict(r) for r in precos],
            }

    # ------------------------------------------------------------------
    # Pedidos de compra
    # ------------------------------------------------------------------

    def gerar_pedidos(self, cotacao_id: int, logica: str) -> list[dict]:
        """Gera pedidos consolidados por fornecedor. logica: fracionado|centralizado."""
        logica = "centralizado" if logica == "centralizado" else "fracionado"
        with system_conn() as conn:
            itens = conn.execute(
                "SELECT id AS cotacao_item_id, produto_id, descricao, quantidade"
                " FROM cotacao_itens WHERE cotacao_id=? ORDER BY id",
                (cotacao_id,),
            ).fetchall()
            precos = conn.execute(
                """SELECT cp.cotacao_item_id, cp.fornecedor_id, cp.preco_unitario,
                          cp.desconto FROM cotacao_precos cp
                   JOIN cotacao_itens ci ON ci.id=cp.cotacao_item_id
                   WHERE ci.cotacao_id=? AND cp.disponibilidade_estoque=1""",
                (cotacao_id,),
            ).fetchall()

            escolhas: dict[int, dict] = {}
            if logica == "centralizado":
                escolhas = self._escolha_centralizada(itens, precos)
            else:
                escolhas = self._escolha_fracionada(itens, precos)

            conn.execute("DELETE FROM pedido_itens WHERE cotacao_id=?", (cotacao_id,))
            # não apaga pedidos_compra antigos; cria novos no fechamento.
            agrupados: dict[int, list[dict]] = {}
            for item in itens:
                c = escolhas.get(item["cotacao_item_id"])
                if not c:
                    continue
                agrupados.setdefault(c["fornecedor_id"], []).append(
                    {**item, **c}
                )

            pedidos = []
            numero_base = conn.execute("SELECT COALESCE(MAX(CAST(numero AS INTEGER)), 0) FROM pedidos_compra").fetchone()[0]
            for i, (fid, linhas) in enumerate(sorted(agrupados.items()), start=1):
                numero = str(numero_base + i).zfill(4)
                cur = conn.execute(
                    "INSERT INTO pedidos_compra (numero, cotacao_id, fornecedor_id,"
                    " status, observacoes, data_geracao) VALUES (?,?,?,'enviado',?, datetime('now'))",
                    (numero, cotacao_id, fid, f"Cotação {cotacao_id} · {logica}"),
                )
                pedido_id = cur.lastrowid
                total = 0.0
                for ln in linhas:
                    conn.execute(
                        """INSERT INTO pedido_itens (cotacao_id, cotacao_item_id, pedido_id,
                             fornecedor_id, preco_unitario, quantidade)
                           VALUES (?,?,?,?,?,?)""",
                        (cotacao_id, ln["cotacao_item_id"], pedido_id, fid,
                         ln["preco_liquido"], ln["quantidade"]),
                    )
                    total += ln["preco_liquido"] * ln["quantidade"]
                nome = conn.execute("SELECT nome FROM fornecedores WHERE id=?", (fid,)).fetchone()["nome"]
                pedidos.append({
                    "id": pedido_id, "numero": numero, "fornecedor_id": fid,
                    "fornecedor": nome, "total": total, "n_itens": len(linhas),
                    "status": "enviado",
                })
            conn.execute(
                "UPDATE cotacoes SET status='finalizada', fechado_em=datetime('now') WHERE id=?",
                (cotacao_id,),
            )
            return pedidos

    # ------------------------------------------------------------------

    def _preco_liquido(self, row) -> float:
        desc = float(row["desconto"] or 0)
        return float(row["preco_unitario"]) * (1 - desc / 100.0)

    def _escolha_fracionada(self, itens, precos) -> dict[int, dict]:
        idx: dict[int, list] = {}
        for p in precos:
            idx.setdefault(p["cotacao_item_id"], []).append(p)
        escolhas = {}
        for item in itens:
            cands = [p for p in idx.get(item["cotacao_item_id"], [])
                     if float(p["preco_unitario"]) > 0]
            if not cands:
                continue
            best = min(cands, key=self._preco_liquido)
            escolhas[item["cotacao_item_id"]] = {
                "fornecedor_id": best["fornecedor_id"],
                "preco_liquido": self._preco_liquido(best),
                "quantidade": item["quantidade"],
            }
        return escolhas

    def _escolha_centralizada(self, itens, precos) -> dict[int, dict]:
        item_ids = [it["cotacao_item_id"] for it in itens]
        # só fornecedores que precificaram TODOS os itens entram como candidato
        holders: dict[int, dict] = {}
        for it in itens:
            key = it["cotacao_item_id"]
            for p in precos:
                if p["cotacao_item_id"] != key or float(p["preco_unitario"]) <= 0:
                    continue
                if p["fornecedor_id"] not in holders:
                    holders[p["fornecedor_id"]] = {}
                holders[p["fornecedor_id"]][key] = p
        qualificados = [fid for fid, mapa in holders.items()
                        if all(k in mapa for k in item_ids)]
        if not qualificados:
            return {}
        totals = {
            fid: sum(self._preco_liquido(holders[fid][k]) for k in item_ids)
            for fid in qualificados
        }
        vencedor = min(totals, key=totals.get)
        return {
            it["cotacao_item_id"]: {
                "fornecedor_id": vencedor,
                "preco_liquido": self._preco_liquido(holders[vencedor][it["cotacao_item_id"]]),
                "quantidade": it["quantidade"],
            }
            for it in itens
        }

    # ------------------------------------------------------------------
    # Consulta de pedidos
    # ------------------------------------------------------------------

    def list_pedidos(self) -> list[dict]:
        with system_conn() as conn:
            rows = conn.execute(
                """SELECT p.*, f.nome AS fornecedor, c.numero AS cotacao_numero,
                          c.titulo AS cotacao_titulo,
                          (SELECT COUNT(*) FROM pedido_itens pi WHERE pi.pedido_id=p.id) AS n_itens
                   FROM pedidos_compra p
                   JOIN fornecedores f ON f.id=p.fornecedor_id
                   JOIN cotacoes c ON c.id=p.cotacao_id
                   ORDER BY p.criado_em DESC""",
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                tot = conn.execute(
                    "SELECT SUM(preco_unitario*quantidade) t FROM pedido_itens WHERE pedido_id=?",
                    (d["id"],),
                ).fetchone()["t"]
                d["total"] = tot or 0
                out.append(d)
            return out

    def get_pedido(self, pedido_id: int) -> dict | None:
        with system_conn() as conn:
            p = conn.execute(
                """SELECT p.*, f.nome AS fornecedor, f.whatsapp, f.email, f.cnpj_cpf,
                          f.razao_social, f.representante,
                          c.numero AS cotacao_numero, c.titulo AS cotacao_titulo,
                          cf.condicao_pagamento, cf.condicao_pagamento_dias
                   FROM pedidos_compra p
                   JOIN fornecedores f ON f.id=p.fornecedor_id
                   JOIN cotacoes c ON c.id=p.cotacao_id
                   LEFT JOIN cotacao_fornecedores cf
                          ON cf.cotacao_id=p.cotacao_id AND cf.fornecedor_id=p.fornecedor_id
                   WHERE p.id=?""",
                (pedido_id,),
            ).fetchone()
            if p is None:
                return None
            itens = conn.execute(
                """SELECT pi.*, ci.produto_id, ci.descricao,
                          cp.unidade_compra, cp.fator_conversao, cp.marca_ofertada,
                          cp.motivo_indisponibilidade
                   FROM pedido_itens pi
                   JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id
                   LEFT JOIN cotacao_precos cp
                          ON cp.cotacao_item_id=pi.cotacao_item_id
                         AND cp.fornecedor_id=pi.fornecedor_id
                   WHERE pi.pedido_id=? ORDER BY pi.id""",
                (pedido_id,),
            ).fetchall()
            d = dict(p)
            d["itens"] = [dict(r) for r in itens]
            d["total"] = sum(r["preco_unitario"] * r["quantidade"] for r in itens)
            return d

    def confirmar_recebimento(self, pedido_id: int, deposito_id: int = 1, usuario_id: int | None = None,
                              condicao_pagamento_id: int | None = None) -> dict:
        """Recebe o pedido: entrada de estoque + contas a pagar + status.

        Quando `condicao_pagamento_id` é informado e possui parcelas, gera as
        contas a pagar PARCELADAS (modelo TOTVS/desdobramento) vinculadas ao
        pedido (`origem_tipo='pedido_compra'`) por `grupo_id`. Sem condição,
        cria 1 conta com vencimento em 30 dias.
        """
        with system_conn() as conn:
            pedido = conn.execute("SELECT * FROM pedidos_compra WHERE id=?", (pedido_id,)).fetchone()
            if not pedido:
                raise ValueError("Pedido não encontrado")
            if pedido["status"] != "enviado":
                raise ValueError("Pedido já recebido")
            itens = conn.execute(
                """SELECT pi.*, ci.produto_id FROM pedido_itens pi
                   JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id
                   WHERE pi.pedido_id=?""",
                (pedido_id,),
            ).fetchall()
            total = 0.0
            for item in itens:
                qtd = float(item["quantidade"] or 0)
                preco = float(item["preco_unitario"] or 0)
                total += preco * qtd
                vid = item["produto_id"]
                if vid and qtd > 0:
                    from catalog_server.repositories.estoque import estoque_repo
                    estoque_repo.movimentar(deposito_id, vid, "entrada", qtd, str(pedido["numero"]), "Recebimento compra", usuario_id=usuario_id, _conn=conn)
            from catalog_server.repositories.financeiro import contas_repo
            fornecedor = conn.execute("SELECT nome FROM fornecedores WHERE id=?", (pedido["fornecedor_id"],)).fetchone()
            fnome = fornecedor["nome"] if fornecedor else f"fornecedor #{pedido['fornecedor_id']}"
            from datetime import datetime, timedelta
            from catalog_server.services import lancamentos_lote

            grupo = lancamentos_lote.novo_grupo()
            parcelas = []
            if condicao_pagamento_id:
                try:
                    parcelas = lancamentos_lote.calcular_parcelas(
                        "condicao", round(total, 2), datetime.now().strftime("%Y-%m-%d"),
                        condicao_id=int(condicao_pagamento_id),
                    )
                except ValueError:
                    parcelas = []
            if not parcelas:
                venc = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                parcelas = [{"valor": round(total, 2), "vencimento": venc, "dias": 30}]
            n = len(parcelas)
            for i, p in enumerate(parcelas, start=1):
                descricao = f"Pedido {pedido['numero']}"
                if n > 1:
                    descricao = f"{descricao} — parcela {i}/{n}"
                conn.execute(
                    """INSERT INTO contas_pagar
                         (fornecedor, fornecedor_id, descricao, valor, saldo,
                          data_vencimento, documento, origem_tipo, origem_id,
                          parcela, total_parcelas, grupo_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (fnome, pedido["fornecedor_id"], descricao, float(p["valor"]),
                     float(p["valor"]), p["vencimento"], pedido["numero"],
                     "pedido_compra", pedido_id, i, n, grupo),
                )
            conn.execute("UPDATE pedidos_compra SET status='recebido' WHERE id=?", (pedido_id,))
            return {"ok": True, "total": round(total, 2), "itens": len(itens),
                    "parcelas": n, "grupo_id": grupo}