from __future__ import annotations

from catalog_server.db import system_conn


class CaixaRepository:

    def _ultimo_saldo(self, conn) -> float:
        row = conn.execute(
            "SELECT saldo_posterior FROM caixa_movimento ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return float(row["saldo_posterior"]) if row else 0.0

    def saldo_atual(self) -> float:
        with system_conn() as conn:
            return self._ultimo_saldo(conn)

    def movimentos(self, limit: int = 100, tipo: str | None = None) -> list[dict]:
        sql = "SELECT * FROM caixa_movimento"
        args: list = []
        if tipo:
            sql += " WHERE tipo = ?"
            args.append(tipo)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def movimentar(
        self,
        tipo: str,
        descricao: str,
        valor: float,
        forma_pagamento: str = "dinheiro",
        plano_conta_id: int | None = None,
        documento: str | None = None,
        orcamento_id: int | None = None,
        usuario_id: int | None = None,
        bandeira: str | None = None,
        codigo_autorizacao: str | None = None,
        _conn=None,
    ) -> dict:
        if valor <= 0:
            raise ValueError("Valor deve ser positivo")
        if _conn is None:
            with system_conn() as conn:
                return self.movimentar(
                    tipo, descricao, valor, forma_pagamento, plano_conta_id,
                    documento, orcamento_id, usuario_id, bandeira,
                    codigo_autorizacao, _conn=conn,
                )

        # Serializa o ledger mesmo quando ainda não existe uma linha para
        # bloquear. O lock transacional termina automaticamente no commit.
        _conn.execute("SELECT pg_advisory_xact_lock(804271)")
        saldo_ant = self._ultimo_saldo(_conn)
        if tipo in ("abertura", "entrada", "suprimento"):
            saldo_novo = saldo_ant + valor
        elif tipo in ("saida", "sangria"):
            if valor > saldo_ant:
                raise ValueError("Saldo de caixa insuficiente")
            saldo_novo = saldo_ant - valor
        else:
            raise ValueError(f"Tipo de movimento de caixa inválido: {tipo}")

        cur = _conn.execute(
            "INSERT INTO caixa_movimento (tipo, descricao, valor, saldo_anterior, saldo_posterior,"
            " forma_pagamento, plano_conta_id, documento, orcamento_id, usuario_id,"
            " bandeira, codigo_autorizacao)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (tipo, descricao, valor, saldo_ant, saldo_novo,
             forma_pagamento, plano_conta_id, documento, orcamento_id, usuario_id,
             bandeira, codigo_autorizacao),
        )
        return {"id": cur.lastrowid, "saldo_anterior": saldo_ant, "saldo_posterior": saldo_novo}


class ContasRepository:

    def listar_receber(
        self, status: str | None = None, cliente_id: int | None = None, vencimento_ate: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM contas_receber WHERE 1=1"
        args: list = []
        if status:
            sql += " AND status = ?"
            args.append(status)
        if cliente_id:
            sql += " AND cliente_id = ?"
            args.append(cliente_id)
        if vencimento_ate:
            sql += " AND data_vencimento <= ?"
            args.append(vencimento_ate)
        sql += " ORDER BY data_vencimento, cliente"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get_receber(self, conta_id: int) -> dict | None:
        """Conta a receber enriquecida com dados do cliente (doc/email)."""
        with system_conn() as conn:
            row = conn.execute(
                """SELECT cr.*, c.doc AS cliente_doc, c.email AS cliente_email, c.tipo_pessoa
                   FROM contas_receber cr
                   LEFT JOIN clientes c ON c.id=cr.cliente_id
                   WHERE cr.id=?""",
                (conta_id,),
            ).fetchone()
            return dict(row) if row else None

    def criar_receber(
        self,
        cliente: str, valor: float, data_vencimento: str,
        cliente_id: int | None = None, descricao: str = "",
        documento: str | None = None, plano_conta_id: int | None = None,
        observacao: str | None = None,
        _conn=None,
    ) -> int:
        if float(valor) <= 0:
            raise ValueError("Valor deve ser positivo")
        if _conn is None:
            with system_conn() as conn:
                return self.criar_receber(
                    cliente, valor, data_vencimento, cliente_id, descricao,
                    documento, plano_conta_id, observacao, _conn=conn,
                )
        cur = _conn.execute(
            "INSERT INTO contas_receber (cliente, cliente_id, descricao, valor, saldo,"
            " data_vencimento, documento, plano_conta_id, observacao)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (cliente.strip(), cliente_id, descricao.strip(), valor, valor,
             data_vencimento, documento, plano_conta_id, observacao),
        )
        return cur.lastrowid

    def receber(
        self, conta_id: int, valor_recebido: float,
        data_recebimento: str | None = None, _conn=None,
    ) -> dict:
        if valor_recebido <= 0:
            raise ValueError("Valor recebido deve ser positivo")
        if _conn is None:
            with system_conn() as conn:
                return self.receber(conta_id, valor_recebido, data_recebimento, _conn=conn)
        conta = _conn.execute(
            "SELECT * FROM contas_receber WHERE id=? FOR UPDATE", (conta_id,)
        ).fetchone()
        if not conta:
            raise ValueError("Conta não encontrada")
        saldo_atual = float(conta["saldo"] or 0)
        if valor_recebido > saldo_atual:
            raise ValueError("Valor recebido excede o saldo da conta")
        novo_saldo = saldo_atual - valor_recebido
        novo_status = "pago" if novo_saldo <= 0 else "parcial"
        _conn.execute(
            "UPDATE contas_receber SET saldo=?, status=?, data_recebimento=COALESCE(?, data_recebimento) WHERE id=?",
            (novo_saldo, novo_status, data_recebimento or "", conta_id),
        )
        return {"saldo_anterior": saldo_atual, "saldo_posterior": novo_saldo, "status": novo_status}

    def receber_por_documento(self, documento: str, valor_recebido: float, data_recebimento: str | None = None) -> dict:
        """Baixa as contas a receber associadas a um documento (nº do orçamento).

        Aplica o valor recebido nas contas em aberto/parcial na ordem, retornando
        o valor excedente (troco) que sobrou após quitar todas.
        """
        if valor_recebido <= 0:
            raise ValueError("Valor recebido deve ser positivo")
        with system_conn() as conn:
            contas = conn.execute(
                "SELECT * FROM contas_receber WHERE documento=? AND status IN ('aberto','parcial')"
                " ORDER BY id FOR UPDATE",
                (documento,),
            ).fetchall()
            restante = valor_recebido
            baixadas = 0
            for conta in contas:
                if restante <= 0:
                    break
                saldo = float(conta["saldo"] or 0)
                abatido = min(restante, saldo)
                novo_saldo = max(0.0, saldo - abatido)
                novo_status = "pago" if novo_saldo <= 0 else "parcial"
                conn.execute(
                    "UPDATE contas_receber SET saldo=?, status=?, data_recebimento=COALESCE(?, data_recebimento) WHERE id=?",
                    (novo_saldo, novo_status, data_recebimento or "", conta["id"]),
                )
                restante -= abatido
                baixadas += 1
            return {"contas": baixadas, "excedente": round(max(0.0, restante), 2)}

    def cancelar_por_documento(self, documento: str) -> int:
        """Cancela as contas a receber ainda em aberto/parcial de um documento."""
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE contas_receber SET status='cancelado'"
                " WHERE documento=? AND status IN ('aberto','parcial')",
                (documento,),
            )
            return cur.rowcount

    def listar_pagar(
        self, status: str | None = None, fornecedor_id: int | None = None, vencimento_ate: str | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM contas_pagar WHERE 1=1"
        args: list = []
        if status:
            sql += " AND status = ?"
            args.append(status)
        if fornecedor_id:
            sql += " AND fornecedor_id = ?"
            args.append(fornecedor_id)
        if vencimento_ate:
            sql += " AND data_vencimento <= ?"
            args.append(vencimento_ate)
        sql += " ORDER BY data_vencimento, fornecedor"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def criar_pagar(
        self,
        fornecedor: str, valor: float, data_vencimento: str,
        fornecedor_id: int | None = None, descricao: str = "",
        documento: str | None = None, plano_conta_id: int | None = None,
        observacao: str | None = None,
        _conn=None,
    ) -> int:
        ctx = system_conn() if _conn is None else None
        conn = _conn or ctx.__enter__()
        try:
            cur = conn.execute(
                "INSERT INTO contas_pagar (fornecedor, fornecedor_id, descricao, valor, saldo,"
                " data_vencimento, documento, plano_conta_id, observacao)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (fornecedor.strip(), fornecedor_id, descricao.strip(), valor, valor,
                 data_vencimento, documento, plano_conta_id, observacao),
            )
            return cur.lastrowid
        finally:
            if ctx:
                ctx.__exit__(None, None, None)

    def pagar(self, conta_id: int, valor_pago: float, data_pagamento: str | None = None) -> dict:
        if valor_pago <= 0:
            raise ValueError("Valor pago deve ser positivo")
        with system_conn() as conn:
            conta = conn.execute(
                "SELECT * FROM contas_pagar WHERE id=? FOR UPDATE", (conta_id,)
            ).fetchone()
            if not conta:
                raise ValueError("Conta não encontrada")
            saldo_atual = float(conta["saldo"] or 0)
            if valor_pago > saldo_atual:
                raise ValueError("Valor pago excede o saldo da conta")
            novo_saldo = saldo_atual - valor_pago
            novo_status = "pago" if novo_saldo <= 0 else "parcial"
            conn.execute(
                "UPDATE contas_pagar SET saldo=?, status=?, data_pagamento=COALESCE(?, data_pagamento) WHERE id=?",
                (novo_saldo, novo_status, data_pagamento or "", conta_id),
            )
            return {"saldo_anterior": saldo_atual, "saldo_posterior": novo_saldo, "status": novo_status}


caixa_repo = CaixaRepository()
contas_repo = ContasRepository()


class CondicaoRepository:

    def list(self, somente_ativas: bool = False) -> list[dict]:
        sql = "SELECT * FROM condicoes_pagamento"
        args: list = []
        if somente_ativas:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, condicao_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM condicoes_pagamento WHERE id=?", (condicao_id,)).fetchone()
            return dict(row) if row else None

    def create(self, nome: str, descricao: str = "") -> int:
        with system_conn() as conn:
            cur = conn.execute("INSERT INTO condicoes_pagamento (nome, descricao) VALUES (?,?)", (nome.strip(), descricao.strip()))
            return cur.lastrowid

    def update(self, condicao_id: int, nome: str, descricao: str) -> bool:
        with system_conn() as conn:
            return conn.execute("UPDATE condicoes_pagamento SET nome=?, descricao=? WHERE id=?", (nome.strip(), descricao.strip(), condicao_id)).rowcount > 0

    def set_ativo(self, condicao_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            return conn.execute("UPDATE condicoes_pagamento SET ativo=? WHERE id=?", (int(ativo), condicao_id)).rowcount > 0

    def list_parcelas(self, condicao_id: int) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM condicao_parcelas WHERE condicao_id=? ORDER BY sequencia", (condicao_id,)
            ).fetchall()]

    def upsert_parcela(self, condicao_id: int, sequencia: int, dias: int, percentual: float) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO condicao_parcelas (condicao_id, sequencia, dias, percentual) VALUES (?,?,?,?)",
                (condicao_id, sequencia, dias, percentual),
            )
            return cur.lastrowid

    def limpar_parcelas(self, condicao_id: int) -> None:
        with system_conn() as conn:
            conn.execute("DELETE FROM condicao_parcelas WHERE condicao_id=?", (condicao_id,))


class CentroCustoRepository:

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM centros_custo"
        args: list = []
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY codigo"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(self, codigo: str, nome: str) -> int:
        with system_conn() as conn:
            return conn.execute("INSERT INTO centros_custo (codigo, nome) VALUES (?,?)", (codigo.strip(), nome.strip())).lastrowid

    def update(self, cc_id: int, codigo: str, nome: str) -> bool:
        with system_conn() as conn:
            return conn.execute("UPDATE centros_custo SET codigo=?, nome=? WHERE id=?", (codigo.strip(), nome.strip(), cc_id)).rowcount > 0

    def set_ativo(self, cc_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            return conn.execute("UPDATE centros_custo SET ativo=? WHERE id=?", (int(ativo), cc_id)).rowcount > 0


class AdiantamentoRepository:

    def list(self, tipo: str | None = None) -> list[dict]:
        sql = "SELECT * FROM adiantamentos"
        args: list = []
        if tipo:
            sql += " WHERE tipo = ?"
            args.append(tipo)
        sql += " ORDER BY data_adiantamento DESC"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(self, tipo: str, pessoa_nome: str, valor: float, data_adiantamento: str, pessoa_id: int | None = None, observacao: str = "") -> int:
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO adiantamentos (tipo, pessoa_id, pessoa_nome, valor, saldo, data_adiantamento, observacao)"
                " VALUES (?,?,?,?,?,?,?)",
                (tipo, pessoa_id, pessoa_nome.strip(), valor, valor, data_adiantamento, observacao.strip()),
            ).lastrowid

    def baixar(self, adiantamento_id: int, valor: float, data_baixa: str) -> dict:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM adiantamentos WHERE id=?", (adiantamento_id,)).fetchone()
            if not row:
                raise ValueError("Adiantamento não encontrado")
            novo_saldo = max(0, float(row["saldo"] or 0) - valor)
            conn.execute(
                "UPDATE adiantamentos SET saldo=?, data_baixa=? WHERE id=?",
                (novo_saldo, data_baixa, adiantamento_id),
            )
            return {"saldo_anterior": row["saldo"], "saldo_posterior": novo_saldo}


condicao_repo = CondicaoRepository()
centro_custo_repo = CentroCustoRepository()
adiantamento_repo = AdiantamentoRepository()
