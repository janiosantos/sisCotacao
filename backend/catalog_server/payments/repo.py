"""Acesso aos provedores de pagamento configurados (migração 0083)."""
from __future__ import annotations

from catalog_server.db import system_conn


class PaymentProviderRepo:

    def list_providers(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM payment_provider ORDER BY nome"
            ).fetchall()]

    def list_configs(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                """SELECT c.*, p.codigo AS provider_codigo, p.nome AS provider_nome
                   FROM payment_provider_config c
                   JOIN payment_provider p ON p.id=c.provider_id
                   ORDER BY p.nome, c.operacao, c.prioridade"""
            ).fetchall()]

    def get_config(self, provider_codigo: str, operacao: str, ambiente: str) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                """SELECT c.* FROM payment_provider_config c
                   JOIN payment_provider p ON p.id=c.provider_id
                   WHERE p.codigo=? AND c.operacao=? AND c.ambiente=?
                     AND c.ativo=1 LIMIT 1""",
                (provider_codigo, operacao, ambiente),
            ).fetchone()
            return dict(row) if row else None

    def escolher(self, operacao: str, ambiente: str) -> dict | None:
        """Provedor de menor prioridade (custo) ativo para a operação/ambiente."""
        with system_conn() as conn:
            row = conn.execute(
                """SELECT c.*, p.codigo AS provider_codigo, p.nome AS provider_nome
                   FROM payment_provider_config c
                   JOIN payment_provider p ON p.id=c.provider_id
                   WHERE c.operacao=? AND c.ambiente=? AND c.ativo=1
                   ORDER BY c.prioridade ASC, c.id ASC LIMIT 1""",
                (operacao, ambiente),
            ).fetchone()
            return dict(row) if row else None

    def upsert_config(self, dados: dict) -> int:
        with system_conn() as conn:
            provider_id = int(dados["provider_id"])
            operacao = dados["operacao"]
            ambiente = dados["ambiente"]
            cur = conn.execute(
                """INSERT INTO payment_provider_config
                     (provider_id, operacao, ambiente, client_id, client_secret,
                      access_token, api_key, certificado, conta, chave_pix,
                      prioridade, ativo)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT (provider_id, operacao, ambiente) DO UPDATE SET
                     client_id=excluded.client_id, client_secret=excluded.client_secret,
                     access_token=excluded.access_token, api_key=excluded.api_key,
                     certificado=excluded.certificado, conta=excluded.conta,
                     chave_pix=excluded.chave_pix, prioridade=excluded.prioridade,
                     ativo=excluded.ativo""",
                (
                    provider_id, operacao, ambiente,
                    dados.get("client_id") or "", dados.get("client_secret") or "",
                    dados.get("access_token") or "", dados.get("api_key") or "",
                    dados.get("certificado") or "", dados.get("conta") or "",
                    dados.get("chave_pix") or "", int(dados.get("prioridade") or 10),
                    int(dados.get("ativo", 1)),
                ),
            )
            return cur.lastrowid


payment_provider_repo = PaymentProviderRepo()