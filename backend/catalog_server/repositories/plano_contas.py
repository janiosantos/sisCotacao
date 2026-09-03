from __future__ import annotations

from catalog_server.db import system_conn


class PlanoContasRepository:

    def list(
        self,
        tipo: str | None = None,
        somente_ativos: bool = False,
        natureza: str | None = None,
        rateavel: bool | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM plano_de_contas"
        where: list[str] = []
        args: list = []
        if tipo:
            where.append("tipo = ?")
            args.append(tipo)
        if somente_ativos:
            where.append("ativo = 1")
        if natureza:
            where.append("natureza_custo = ?")
            args.append(natureza)
        if rateavel is not None:
            where.append("permite_rateio = ?")
            args.append(int(rateavel))
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY codigo, nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    # ------------------------------------------------------------------

    def get(self, conta_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM plano_de_contas WHERE id = ?", (conta_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------

    def create(
        self, codigo: str, nome: str, tipo: str, pai_id: int | None,
        natureza_custo: str | None = None, politica_rateio: str | None = None,
        exige_centro_custo: bool = False, exige_competencia: bool = False,
        permite_rateio: bool = False, componente_variavel: str | None = None,
        atualizado_por: int | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO plano_de_contas (codigo, nome, tipo, pai_id, natureza_custo,"
                " politica_rateio, exige_centro_custo, exige_competencia, permite_rateio,"
                " componente_variavel, atualizado_por) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (codigo, nome, tipo, pai_id or None, natureza_custo or "fora_precificacao",
                 politica_rateio or "nao_incluir", exige_centro_custo, exige_competencia,
                 permite_rateio, componente_variavel, atualizado_por),
            )
            return cur.lastrowid

    # ------------------------------------------------------------------

    def update(
        self, conta_id: int, codigo: str, nome: str, tipo: str, pai_id: int | None,
        natureza_custo: str | None = None, politica_rateio: str | None = None,
        exige_centro_custo: bool = False, exige_competencia: bool = False,
        permite_rateio: bool = False, componente_variavel: str | None = None,
        atualizado_por: int | None = None,
    ) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE plano_de_contas SET codigo=?, nome=?, tipo=?, pai_id=?,"
                " natureza_custo=?, politica_rateio=?, exige_centro_custo=?,"
                " exige_competencia=?, permite_rateio=?, componente_variavel=?,"
                " atualizado_por=?, atualizado_em=now() WHERE id=?",
                (codigo, nome, tipo, pai_id or None, natureza_custo or "fora_precificacao",
                 politica_rateio or "nao_incluir", exige_centro_custo, exige_competencia,
                 permite_rateio, componente_variavel, atualizado_por, conta_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------

    def set_ativo(self, conta_id: int, ativo: bool) -> bool:
        with system_conn() as conn:
            cur = conn.execute(
                "UPDATE plano_de_contas SET ativo=?, atualizado_em=datetime('now')"
                " WHERE id=?",
                (int(ativo), conta_id),
            )
            return cur.rowcount > 0

    def uso(self, conta_id: int) -> dict | None:
        with system_conn() as conn:
            conta = conn.execute("SELECT id, codigo, nome, tipo, ativo FROM plano_de_contas WHERE id=?", (conta_id,)).fetchone()
            if not conta:
                return None
            pagar = conn.execute("SELECT COUNT(*) AS n FROM contas_pagar WHERE plano_conta_id=?", (conta_id,)).fetchone()["n"]
            receber = conn.execute("SELECT COUNT(*) AS n FROM contas_receber WHERE plano_conta_id=?", (conta_id,)).fetchone()["n"]
            return {**dict(conta), "contas_pagar": int(pagar or 0), "contas_receber": int(receber or 0)}


plano_conta_repo = PlanoContasRepository()
