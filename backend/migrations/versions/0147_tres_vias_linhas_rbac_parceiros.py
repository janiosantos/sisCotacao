"""Migração 0147 — linha do pedido na conferência e aprovação financeira de parceiros."""
from __future__ import annotations

import json

VERSION = 147
RISCO = "moderada"
NAME = "tres_vias_linhas_rbac_parceiros"

MUDANCA = {
    "o_que": [
        "Vincula divergências de recebimento à linha do pedido, não apenas ao produto",
        "Concede aprovação de bônus ao perfil Financeiro",
    ],
    "porque": [
        "Evita misturar duas linhas do mesmo produto na conferência",
        "Separa operação comercial de aprovação financeira",
    ],
}


def guard(conn) -> bool:
    col = conn.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
        "AND table_name='recebimento_divergencia' AND column_name='pedido_item_id'"
    ).fetchone()
    grant = conn.execute(
        "SELECT 1 FROM perfil_recurso pr JOIN recursos r ON r.id=pr.recurso_id "
        "JOIN perfis p ON p.id=pr.perfil_id WHERE r.codigo='parceiros' AND p.nome='Financeiro' "
        "AND pr.acoes @> %s::jsonb",
        (json.dumps(["aprovar"]),),
    ).fetchone()
    return bool(col and grant)


def forward(conn) -> None:
    conn.execute(
        "ALTER TABLE recebimento_divergencia ADD COLUMN IF NOT EXISTS pedido_item_id BIGINT "
        "REFERENCES pedido_itens(id)"
    )
    conn.execute("ALTER TABLE recebimento_divergencia DROP CONSTRAINT IF EXISTS uq_receb_diverg")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_receb_diverg_linha "
        "ON recebimento_divergencia (recebimento_id, pedido_item_id, tipo)"
    )
    conn.execute(
        "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes) "
        "SELECT p.id, r.id, %s::jsonb FROM perfis p CROSS JOIN recursos r "
        "WHERE p.nome='Financeiro' AND r.codigo='parceiros' "
        "ON CONFLICT (perfil_id, recurso_id) DO UPDATE SET acoes = "
        "(SELECT jsonb_agg(DISTINCT value) FROM jsonb_array_elements_text(" 
        "perfil_recurso.acoes || EXCLUDED.acoes) value)",
        (json.dumps(["visualizar", "aprovar"]),),
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP INDEX IF EXISTS uq_receb_diverg_linha")
    conn.execute("ALTER TABLE recebimento_divergencia DROP COLUMN IF EXISTS pedido_item_id")
