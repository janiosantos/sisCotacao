from __future__ import annotations

from catalog_server.db import system_conn


class BancoRepository:

    def listar_contas(self, somente_ativas: bool = False) -> list[dict]:
        sql = "SELECT * FROM contas_bancarias"
        args: list = []
        if somente_ativas:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get_conta(self, conta_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM contas_bancarias WHERE id=?", (conta_id,)).fetchone()
            return dict(row) if row else None

    def criar_conta(
        self, nome: str, banco: str = "000",
        agencia: str = "", conta: str = "", digito: str = "",
        saldo_inicial: float = 0,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO contas_bancarias (nome, banco, agencia, conta, digito, saldo_inicial, saldo_atual)"
                " VALUES (?,?,?,?,?,?,?)",
                (nome.strip(), banco, agencia, conta, digito, saldo_inicial, saldo_inicial),
            )
            return cur.lastrowid

    def atualizar_conta(
        self, conta_id: int, nome: str, banco: str,
        agencia: str, conta: str, digito: str,
    ) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE contas_bancarias SET nome=?, banco=?, agencia=?, conta=?, digito=?"
                " WHERE id=?",
                (nome.strip(), banco, agencia, conta, digito, conta_id),
            )
            return cur.rowcount > 0

    def set_ativo(self, conta_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE contas_bancarias SET ativo=? WHERE id=?", (int(ativo), conta_id)
            )
            return cur.rowcount > 0

    def recalcular_saldo(self, conta_id: int) -> float:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT saldo_inicial FROM contas_bancarias WHERE id=?", (conta_id,)
            ).fetchone()
            if not row:
                return 0
            saldo_ini = float(row["saldo_inicial"] or 0)
            cred = conn.execute(
                "SELECT COALESCE(SUM(valor),0) FROM movimento_bancario WHERE conta_id=? AND tipo='credito'",
                (conta_id,),
            ).fetchone()[0] or 0
            deb = conn.execute(
                "SELECT COALESCE(SUM(valor),0) FROM movimento_bancario WHERE conta_id=? AND tipo IN ('debito','transferencia')",
                (conta_id,),
            ).fetchone()[0] or 0
            saldo = saldo_ini + float(cred) - float(deb)
            conn.execute("UPDATE contas_bancarias SET saldo_atual=? WHERE id=?", (round(saldo, 2), conta_id))
            return round(saldo, 2)

    def listar_movimentos(self, conta_id: int | None = None, limit: int = 200) -> list[dict]:
        sql = (
            "SELECT m.*, c.nome AS conta_nome, c.banco"
            " FROM movimento_bancario m"
            " JOIN contas_bancarias c ON c.id = m.conta_id"
        )
        args: list = []
        if conta_id:
            sql += " WHERE m.conta_id = ?"
            args.append(conta_id)
        sql += " ORDER BY m.data_movimento DESC, m.id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def criar_movimento(
        self, conta_id: int, tipo: str, valor: float,
        data_movimento: str, descricao: str = "",
        documento: str = "", categoria: str = "",
        plano_conta_id: int | None = None,
    ) -> dict:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO movimento_bancario (conta_id, tipo, valor, data_movimento,"
                " descricao, documento, categoria, plano_conta_id)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (conta_id, tipo, valor, data_movimento,
                 descricao.strip(), documento, categoria, plano_conta_id),
            )
            mov_id = cur.lastrowid
            saldo = self.recalcular_saldo(conta_id)
            return {"id": mov_id, "saldo_atual": saldo}

    def toggle_conciliado(self, mov_id: int) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE movimento_bancario SET conciliado = CASE WHEN conciliado THEN 0 ELSE 1 END,"
                " data_conciliacao = CASE WHEN conciliado THEN NULL ELSE datetime('now') END"
                " WHERE id=?",
                (mov_id,),
            )
            return cur.rowcount > 0


banco_repo = BancoRepository()
