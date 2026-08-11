from __future__ import annotations

from catalog_server.db import system_conn


class DepositoRepository:

    def list(self, somente_ativos: bool = False) -> list[dict]:
        sql = "SELECT * FROM depositos"
        args: list = []
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, deposito_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM depositos WHERE id=?", (deposito_id,)).fetchone()
            return dict(row) if row else None

    def create(self, nome: str, tipo: str = "proprio") -> int:
        with system_conn() as conn:
            cur = conn.execute("INSERT INTO depositos (nome, tipo) VALUES (?,?)", (nome.strip(), tipo))
            return cur.lastrowid

    def update(self, deposito_id: int, nome: str, tipo: str | None = None, **loc) -> bool:
        sets = ["nome=?"]
        args = [nome.strip()]
        if tipo:
            sets.append("tipo=?")
            args.append(tipo)
        for k in ("localizacao_rua", "localizacao_prateleira", "localizacao_nivel", "localizacao_vão"):
            if k in loc:
                sets.append(f"{k}=?")
                args.append(loc[k])
        args.append(deposito_id)
        with system_conn() as conn:
            return conn.execute(f"UPDATE depositos SET {', '.join(sets)} WHERE id=?", args).rowcount > 0

    def set_ativo(self, deposito_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute("UPDATE depositos SET ativo=? WHERE id=?", (int(ativo), deposito_id))
            return cur.rowcount > 0


deposito_repo = DepositoRepository()


class ExpedicaoRepository:

    def list(self, deposito_id: int | None = None, status: str | None = None) -> list[dict]:
        sql = "SELECT e.*, d.nome AS deposito_nome FROM expedicao e JOIN depositos d ON d.id=e.deposito_id WHERE 1=1"
        args: list = []
        if deposito_id:
            sql += " AND e.deposito_id = ?"; args.append(deposito_id)
        if status:
            sql += " AND e.status = ?"; args.append(status)
        sql += " ORDER BY e.id DESC"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def create(self, codigo: str, deposito_id: int, transportadora: str = "", observacao: str = "") -> int:
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO expedicao (codigo, deposito_id, transportadora, observacao) VALUES (?,?,?,?)",
                (codigo.strip(), deposito_id, transportadora.strip(), observacao.strip()),
            ).lastrowid

    def update_status(self, exp_id: int, status: str) -> bool:
        with system_conn() as conn:
            return conn.execute("UPDATE expedicao SET status=? WHERE id=?", (status, exp_id)).rowcount > 0

    def add_item(self, exp_id: int, variante_id: int, quantidade: float, orcamento_id: int | None = None) -> int:
        with system_conn() as conn:
            return conn.execute(
                "INSERT INTO expedicao_itens (expedicao_id, variante_id, quantidade, orcamento_id) VALUES (?,?,?,?)",
                (exp_id, variante_id, quantidade, orcamento_id),
            ).lastrowid


expedicao_repo = ExpedicaoRepository()
