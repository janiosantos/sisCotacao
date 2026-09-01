from __future__ import annotations

import uuid

from catalog_server.db import system_conn
from catalog_server.estoque.movimento import MovimentoEstoque


class EstoqueRepository:

    def saldo(
        self,
        deposito_id: int | None = None,
        produto_id: int | None = None,
        termo: str | None = None,
        familia_id: int | None = None,
    ) -> list[dict]:
        produto_id = produto_id if produto_id is not None else produto_id
        sql = (
            "SELECT s.id, s.deposito_id, s.produto_id,"
            " s.quantidade, s.quantidade AS fisico,"
            " s.reserva, s.reserva AS reservado,"
            " COALESCE(s.bloqueado,0) AS bloqueado, COALESCE(s.separacao,0) AS separacao,"
            " COALESCE(s.transito,0) AS transito,"
            " (s.quantidade - s.reserva - COALESCE(s.bloqueado,0) - COALESCE(s.separacao,0)) AS disponivel,"
            " s.atualizado_em, d.nome AS deposito_nome,"
            " p.sku, p.preco, p.nome AS produto_nome, p.marca,"
            " p.familia_id, f.nome AS familia_nome,"
            " p.unidade_venda, p.embalagem, p.fator_conversao, p.ncm,"
            " p.unidade_tributavel, p.localizacao,"
            " s.estoque_minimo, s.estoque_maximo,"
            " CASE WHEN s.estoque_minimo > 0 AND (s.quantidade - s.reserva - COALESCE(s.bloqueado,0) - COALESCE(s.separacao,0)) < s.estoque_minimo THEN 'ruptura'"
            "  WHEN s.estoque_maximo > 0 AND s.quantidade > s.estoque_maximo THEN 'excesso'"
            "  ELSE 'ok' END AS situacao"
            " FROM estoque_saldo s"
            " JOIN depositos d ON d.id = s.deposito_id"
            " JOIN produtos_cadastro p ON p.id = s.produto_id"
            " LEFT JOIN familias f ON f.id = p.familia_id"
        )
        where: list[str] = []
        args: list = []
        if deposito_id is not None:
            where.append("s.deposito_id = ?")
            args.append(deposito_id)
        if produto_id is not None:
            where.append("s.produto_id = ?")
            args.append(produto_id)
        if familia_id is not None:
            where.append("p.familia_id = ?")
            args.append(familia_id)
        if termo:
            where.append("(p.nome LIKE ? OR p.sku LIKE ? OR p.marca LIKE ?)")
            like = f"%{termo}%"
            args.extend([like, like, like])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY p.nome, p.sku"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def movimentar(
        self,
        deposito_id: int,
        produto_id: int,
        tipo: str,
        quantidade: float,
        documento: str | None = None,
        observacao: str | None = None,
        lote_id: int | None = None,
        usuario_id: int | None = None,
        _conn=None,
    ) -> dict:
        produto_id = produto_id
        ctx = system_conn() if _conn is None else None
        conn = _conn or ctx.__enter__()
        closed = False
        try:
            conn.execute("SELECT pg_advisory_xact_lock(804273)")
            saldo_row = conn.execute(
                "SELECT id, quantidade FROM estoque_saldo WHERE deposito_id=? AND produto_id=? FOR UPDATE",
                (deposito_id, produto_id),
            ).fetchone()
            if saldo_row:
                saldo_atual = float(saldo_row["quantidade"] or 0)
                saldo_id = saldo_row["id"]
            else:
                saldo_atual = 0.0
                conn.execute(
                    "INSERT INTO estoque_saldo (deposito_id, produto_id, quantidade, reserva)"
                    " VALUES (?,?,0,0) ON CONFLICT (deposito_id, produto_id) DO NOTHING",
                    (deposito_id, produto_id),
                )
                saldo_id = conn.execute(
                    "SELECT id FROM estoque_saldo WHERE deposito_id=? AND produto_id=?",
                    (deposito_id, produto_id),
                ).fetchone()["id"]

            if tipo in ("entrada", "inventario"):
                novo_saldo = saldo_atual + quantidade
            elif tipo == "saida":
                novo_saldo = max(0, saldo_atual - quantidade)
            elif tipo == "ajuste":
                novo_saldo = max(0, quantidade)
            elif tipo == "transferencia":
                novo_saldo = max(0, saldo_atual - quantidade)
            else:
                novo_saldo = saldo_atual

            conn.execute(
                "UPDATE estoque_saldo SET quantidade=?, atualizado_em=datetime('now') WHERE id=?",
                (novo_saldo, saldo_id),
            )

            cur = conn.execute(
                "INSERT INTO estoque_movimento (deposito_id, produto_id, tipo, quantidade,"
                " saldo_anterior, saldo_posterior, documento, observacao, lote_id, usuario_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    deposito_id,
                    produto_id,
                    tipo,
                    quantidade,
                    saldo_atual,
                    novo_saldo,
                    documento,
                    observacao,
                    lote_id,
                    usuario_id,
                ),
            )

            return {
                "movimento_id": cur.lastrowid,
                "saldo_anterior": saldo_atual,
                "saldo_posterior": novo_saldo,
            }
        except BaseException as exc:
            if ctx:
                ctx.__exit__(type(exc), exc, exc.__traceback__)
                closed = True
            raise
        finally:
            if ctx and not closed:
                ctx.__exit__(None, None, None)

    def movimentar_fato(
        self,
        deposito_id: int,
        produto_id: int,
        tipo: str,
        quantidade: float,
        *,
        idempotency_key: str | None = None,
        origem_tipo: str = "",
        origem_id: int | None = None,
        documento: str | None = None,
        observacao: str | None = None,
        lote_id: int | None = None,
        usuario_id: int | None = None,
        _conn=None,
    ) -> dict:
        """Fato de estoque idempotente (ADR 0003): retrida com a mesma
        `idempotency_key` devolve o movimento original sem reprocessar.
        Tipos reserva/liberacao movem a coluna RESERVA, não o saldo."""
        produto_id = produto_id
        if not idempotency_key:
            idempotency_key = f"auto-{uuid.uuid4().hex}"

        tipos_positivos = {"entrada", "saida", "reserva", "liberacao", "ajuste", "transferencia"}
        if tipo in tipos_positivos and float(quantidade) <= 0:
            raise ValueError("Quantidade deve ser positiva")
        if tipo not in tipos_positivos and tipo != "inventario":
            raise ValueError(f"tipo desconhecido: {tipo}")

        ctx = system_conn() if _conn is None else None
        conn = _conn or ctx.__enter__()
        closed = False
        try:
            existente = conn.execute(
                "SELECT id, quantidade, saldo_anterior, saldo_posterior"
                " FROM estoque_movimento WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existente:
                return {
                    "movimento_id": existente["id"],
                    "duplicado": True,
                    "saldo_anterior": float(existente["saldo_anterior"] or 0),
                    "saldo_posterior": float(existente["saldo_posterior"] or 0),
                }

            # A linha do saldo é o recurso serializado. O INSERT concorrente é
            # benigno graças à chave única (deposito_id, produto_id); depois
            # dele sempre relê com lock para evitar lost update.
            row = conn.execute(
                "SELECT id, quantidade, reserva FROM estoque_saldo"
                " WHERE deposito_id=? AND produto_id=? FOR UPDATE",
                (deposito_id, produto_id),
            ).fetchone()
            if row:
                saldo_atual = float(row["quantidade"] or 0)
                reserva_atual = float(row["reserva"] or 0)
                saldo_id = row["id"]
            else:
                conn.execute(
                    "INSERT INTO estoque_saldo (deposito_id, produto_id, quantidade, reserva)"
                    " VALUES (?,?,0,0) ON CONFLICT (deposito_id, produto_id) DO NOTHING",
                    (deposito_id, produto_id),
                )
                saldo_atual, reserva_atual = 0.0, 0.0
                saldo_id = conn.execute(
                    "SELECT id, quantidade, reserva FROM estoque_saldo"
                    " WHERE deposito_id=? AND produto_id=? FOR UPDATE",
                    (deposito_id, produto_id),
                ).fetchone()["id"]
                row = conn.execute(
                    "SELECT id, quantidade, reserva FROM estoque_saldo"
                    " WHERE deposito_id=? AND produto_id=? FOR UPDATE",
                    (deposito_id, produto_id),
                ).fetchone()
                saldo_atual = float(row["quantidade"] or 0)
                reserva_atual = float(row["reserva"] or 0)

            # O primeiro check é apenas um fast-path. O segundo ocorre depois
            # do lock e fecha a corrida entre duas requisições idempotentes.
            existente = conn.execute(
                "SELECT id, quantidade, saldo_anterior, saldo_posterior"
                " FROM estoque_movimento WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existente:
                return {
                    "movimento_id": existente["id"],
                    "duplicado": True,
                    "saldo_anterior": float(existente["saldo_anterior"] or 0),
                    "saldo_posterior": float(existente["saldo_posterior"] or 0),
                }

            q = float(quantidade)

            if tipo == "reserva":
                disponivel = saldo_atual - reserva_atual
                if q > disponivel:
                    raise ValueError(
                        f"Estoque disponível insuficiente para reserva: {disponivel:g}"
                    )
                novo_reserva = reserva_atual + q
                conn.execute(
                    "UPDATE estoque_saldo SET reserva=? WHERE id=?",
                    (novo_reserva, saldo_id),
                )
                novo_saldo = saldo_atual
            elif tipo == "liberacao":
                if q > reserva_atual:
                    raise ValueError("Quantidade de liberação excede a reserva atual")
                novo_reserva = reserva_atual - q
                conn.execute(
                    "UPDATE estoque_saldo SET reserva=? WHERE id=?",
                    (novo_reserva, saldo_id),
                )
                novo_saldo = saldo_atual
            else:
                if tipo in ("entrada", "inventario"):
                    novo_saldo = saldo_atual + q
                elif tipo == "saida":
                    disponivel = saldo_atual - reserva_atual
                    if q > disponivel:
                        raise ValueError(
                            f"Estoque disponível insuficiente: {disponivel:g}"
                        )
                    novo_saldo = saldo_atual - q
                elif tipo == "ajuste":
                    novo_saldo = q
                elif tipo == "transferencia":
                    disponivel = saldo_atual - reserva_atual
                    if q > disponivel:
                        raise ValueError(
                            f"Estoque disponível insuficiente: {disponivel:g}"
                        )
                    novo_saldo = saldo_atual - q
                conn.execute(
                    "UPDATE estoque_saldo SET quantidade=?, atualizado_em=datetime('now')"
                    " WHERE id=?",
                    (novo_saldo, saldo_id),
                )

            cur = conn.execute(
                "INSERT INTO estoque_movimento (deposito_id, produto_id, tipo,"
                " quantidade, saldo_anterior, saldo_posterior, documento,"
                " observacao, lote_id, usuario_id, idempotency_key,"
                " origem_tipo, origem_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    deposito_id, produto_id, tipo, quantidade,
                    saldo_atual, novo_saldo, documento, observacao,
                    lote_id, usuario_id, idempotency_key,
                    origem_tipo, origem_id,
                ),
            )
            if ctx is None:
                # A transação pertence ao caso de uso chamador.
                pass
            return {
                "movimento_id": cur.lastrowid,
                "duplicado": False,
                "saldo_anterior": saldo_atual,
                "saldo_posterior": novo_saldo,
                "tipo": tipo,
            }
        except BaseException as exc:
            if ctx is not None:
                ctx.__exit__(type(exc), exc, exc.__traceback__)
                closed = True
            raise
        finally:
            if ctx is not None and not closed:
                ctx.__exit__(None, None, None)

    def reconciliar(self, deposito_id: int, produto_id: int) -> dict:
        produto_id = produto_id
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM reconciliar_estoque(?, ?)",
                (deposito_id, produto_id),
            ).fetchone()
            return dict(row) if row else {}

    def reconciliar_tudo(self, deposito_id: int | None = None) -> list[dict]:
        """Lista saldos com divergência entre o materializado e o derivado
        (chamado pelo gate de CI/staging para alertar desalinhamentos)."""
        sql = (
            "SELECT s.deposito_id, s.produto_id, s.quantidade AS materializado,"
            " COALESCE(d.derivado, 0) AS derivado"
            " FROM estoque_saldo s"
            " LEFT JOIN LATERAL ("
            "   SELECT COALESCE(SUM(CASE WHEN m.tipo IN"
            "     ('entrada','transferencia','inventario') THEN m.quantidade"
            "     ELSE -m.quantidade END),0) AS derivado"
            "   FROM estoque_movimento m WHERE m.deposito_id=s.deposito_id"
            "     AND m.produto_id=s.produto_id"
            " ) d ON TRUE"
        )
        where: list[str] = []
        args: list = []
        if deposito_id is not None:
            where.append("s.deposito_id = ?")
            args.append(deposito_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " AND COALESCE(d.derivado,0) <> s.quantidade"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def lancar_inventario(
        self,
        deposito_id: int,
        produto_id: int,
        quantidade_contada: float,
        *,
        justificativa: str,
        idempotency_key: str | None = None,
        usuario_id: int | None = None,
    ) -> dict:
        """Ajuste por inventário: cria um FATO tipo 'inventario' que leva o
        saldo à quantidade contada (motivo registrado)."""
        produto_id = produto_id
        with system_conn() as conn:
            atual = conn.execute(
                "SELECT quantidade FROM estoque_saldo"
                " WHERE deposito_id=? AND produto_id=?",
                (deposito_id, produto_id),
            ).fetchone()
            saldo_atual = float(atual["quantidade"] or 0) if atual else 0.0
            diff = float(quantidade_contada) - saldo_atual
            if diff == 0:
                return {
                    "movimento_id": None,
                    "duplicado": True,
                    "motivo": "inventário já conferido (sem divergência)",
                }
            if not idempotency_key:
                import uuid

                idempotency_key = f"inv-{uuid.uuid4().hex}"
        # 'inventario' soma a diferença para atingir a contagem
        return self.movimentar_fato(
            deposito_id,
            produto_id,
            "inventario",
            diff,
            idempotency_key=idempotency_key,
            origem_tipo="inventario",
            origem_id=None,
            documento="inventário",
            observacao=justificativa[:500],
            usuario_id=usuario_id,
        )

    def movimentos(
        self,
        deposito_id: int | None = None,
        produto_id: int | None = None,
        tipo: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        produto_id = produto_id
        sql = (
            "SELECT m.*, d.nome AS deposito_nome,"
            " p.sku, p.nome AS produto_nome, p.marca"
            " FROM estoque_movimento m"
            " JOIN depositos d ON d.id = m.deposito_id"
            " JOIN produtos_cadastro p ON p.id = m.produto_id"
        )
        where: list[str] = []
        args: list = []
        if deposito_id is not None:
            where.append("m.deposito_id = ?")
            args.append(deposito_id)
        if produto_id is not None:
            where.append("m.produto_id = ?")
            args.append(produto_id)
        if tipo:
            where.append("m.tipo = ?")
            args.append(tipo)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def transferir(
        self,
        origem_id: int,
        destino_id: int,
        produto_id: int,
        quantidade: float,
        observacao: str | None = None,
        usuario_id: int | None = None,
    ) -> dict:
        with system_conn() as conn:
            self.movimentar(origem_id, produto_id, "transferencia", quantidade, "Transferência", observacao, None, usuario_id, _conn=conn)
            self.movimentar(destino_id, produto_id, "entrada", quantidade, "Transferência", observacao, None, usuario_id, _conn=conn)
        return {"ok": True}


class LoteRepository:

    def list(self, deposito_id: int | None = None, produto_id: int | None = None) -> list[dict]:
        produto_id = produto_id
        sql = (
            "SELECT l.*, d.nome AS deposito_nome,"
            " p.sku, p.nome AS produto_nome, p.marca"
            " FROM lotes l"
            " JOIN depositos d ON d.id = l.deposito_id"
            " JOIN produtos_cadastro p ON p.id = l.produto_id"
        )
        where: list[str] = []
        args: list = []
        if deposito_id is not None:
            where.append("l.deposito_id = ?")
            args.append(deposito_id)
        if produto_id is not None:
            where.append("l.produto_id = ?")
            args.append(produto_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY l.data_validade, l.codigo"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, lote_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM lotes WHERE id=?", (lote_id,)).fetchone()
            return dict(row) if row else None

    def create(
        self,
        deposito_id: int,
        produto_id: int,
        codigo: str,
        quantidade: float = 0,
        data_fabricacao: str | None = None,
        data_validade: str | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO lotes (deposito_id, produto_id, codigo, quantidade, data_fabricacao, data_validade)"
                " VALUES (?,?,?,?,?,?)",
                (deposito_id, produto_id, codigo.strip(), quantidade, data_fabricacao, data_validade),
            )
            return cur.lastrowid


estoque_repo = EstoqueRepository()
lote_repo = LoteRepository()
