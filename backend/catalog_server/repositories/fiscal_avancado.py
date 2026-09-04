from __future__ import annotations

from catalog_server.db import system_conn


COLUNAS_EMITENTE = frozenset({
    "razao_social", "nome_fantasia", "cnpj", "ie", "im", "regime_tributario",
    "cnae_principal", "cnae_secundario", "logradouro", "numero", "bairro",
    "cep", "municipio", "uf", "token_focus", "ambiente_focus",
    "aliquota_icms", "aliquota_pis", "aliquota_cofins", "aliquota_ipi",
    "serie_nfe", "proximo_numero_nfe", "ativo",
    "crt", "aliquota_ibs", "aliquota_cbs",
    "ibs_vigencia_inicio", "ibs_vigencia_fim", "cbs_vigencia_inicio", "cbs_vigencia_fim",
    "c_municipio",
})

class EmitenteRepository:

    def get(self) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM emitente WHERE ativo=1 LIMIT 1").fetchone()
            return dict(row) if row else None

    def upsert(self, dados: dict) -> int:
        dados = {k: v for k, v in dados.items() if k in COLUNAS_EMITENTE}
        if not dados:
            return 0
        with system_conn() as conn:
            existing = conn.execute("SELECT id FROM emitente LIMIT 1").fetchone()
            if existing:
                sets = ", ".join(f"{k}=?" for k in dados)
                vals = list(dados.values()) + [existing["id"]]
                conn.execute(f"UPDATE emitente SET {sets} WHERE id=?", vals)
                return existing["id"]
            cols = ", ".join(dados.keys())
            placeholders = ", ".join("?" for _ in dados)
            cur = conn.execute(
                f"INSERT INTO emitente ({cols}) VALUES ({placeholders}) RETURNING id",
                list(dados.values()),
            )
            return int(cur.fetchone()["id"])


class NfeSaidaRepository:

    def list(self, status: str | None = None) -> list[dict]:
        sql = "SELECT * FROM nfe_saida WHERE 1=1"
        args: list = []
        if status:
            sql += " AND status = ?"; args.append(status)
        sql += " ORDER BY id DESC"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def emitir(
        self,
        orcamento_id: int,
        numero: int,
        serie: int,
        chave: str,
        cliente_nome: str,
        cliente_doc: str,
        valor: float,
        xml: str,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO nfe_saida (numero, serie, chave, status, orcamento_id,"
                " cliente_nome, cliente_doc, valor, xml)"
                " VALUES (?,?,?,'digitada',?,?,?,?,?)",
                (numero, serie, chave, orcamento_id, cliente_nome, cliente_doc, valor, xml),
            )
            conn.execute(
                "UPDATE emitente SET proximo_numero_nfe=proximo_numero_nfe+1 WHERE ativo=1"
            )
            return cur.lastrowid


class NfeEntradaRepository:

    def list(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM nfe_entrada ORDER BY id DESC").fetchall()]


emitente_repo = EmitenteRepository()
nfe_saida_repo = NfeSaidaRepository()
nfe_entrada_repo = NfeEntradaRepository()
