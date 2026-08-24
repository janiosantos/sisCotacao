"""Migração 0081 — RBAC: atualizacoes.visualizar para perfis operacionais.

O smoke test pós-deploy (Regra 12) autentica um usuário de perfil vendedor e
consulta `GET /api/sistema/status`. O RBAC (migração 0075) concedeu
`atualizacoes` apenas implícito ao Administrador (superuser), o que quebra o
smoke para Vendedor/Estoquista/Operador.

Correção: concede `atualizacoes:visualizar` aos perfis operacionais (ver o
status de versão/migrações é leitura inofensiva). Administrador continua
superuser (sem linhas). Idempotente.
"""
from __future__ import annotations

import json

VERSION = 81
RISCO = "rotina"
NAME = "rbac_atualizacoes_visualizar"

MUDANCA = {
    "o_que": [
        "Concede permissão visualizar no recurso 'atualizacoes' aos perfis Vendedor, Estoquista e Operador",
        "Smoke test pós-deploy deixa de falhar no GET /api/sistema/status com usuário vendedor",
    ],
    "porque": [
        "Status de versão/migrações é leitura inofensiva e o painel de Atualizações é usado no dia a dia",
        "Regra 12 (smoke test) autentica perfil vendedor e precisa ler o status",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM perfil_recurso pr"
        " JOIN perfis p ON p.id = pr.perfil_id"
        " JOIN recursos r ON r.id = pr.recurso_id"
        " WHERE p.nome='Vendedor' AND r.codigo='atualizacoes'"
        " AND pr.acoes::jsonb ? 'visualizar'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        for nome_perfil in ("Vendedor", "Estoquista", "Operador"):
            pid = conn.execute(
                "SELECT id FROM perfis WHERE nome=%s", (nome_perfil,)
            ).fetchone()
            if pid is None:
                continue
            rid = conn.execute(
                "SELECT id FROM recursos WHERE codigo='atualizacoes'"
            ).fetchone()
            if rid is None:
                continue
            linha = conn.execute(
                "SELECT acoes FROM perfil_recurso WHERE perfil_id=%s AND recurso_id=%s",
                (pid[0], rid[0]),
            ).fetchone()
            if linha is None:
                conn.execute(
                    "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes)"
                    " VALUES (%s, %s, %s::jsonb)",
                    (pid[0], rid[0], json.dumps(["visualizar"])),
                )
            else:
                atual = linha[0]
                if isinstance(atual, str):
                    atual = json.loads(atual) if atual else []
                acoes = list(atual) if isinstance(atual, list) else []
                if "visualizar" not in acoes:
                    acoes.append("visualizar")
                    conn.execute(
                        "UPDATE perfil_recurso SET acoes=%s::jsonb"
                        " WHERE perfil_id=%s AND recurso_id=%s",
                        (json.dumps(acoes), pid[0], rid[0]),
                    )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    """Remove visualizar de atualizacoes dos perfis operacionais (idempotente)."""
    ac = conn.autocommit
    conn.autocommit = True
    try:
        for nome_perfil in ("Vendedor", "Estoquista", "Operador"):
            pid = conn.execute(
                "SELECT id FROM perfis WHERE nome=%s", (nome_perfil,)
            ).fetchone()
            if pid is None:
                continue
            rid = conn.execute(
                "SELECT id FROM recursos WHERE codigo='atualizacoes'"
            ).fetchone()
            if rid is None:
                continue
            conn.execute(
                "UPDATE perfil_recurso SET acoes = "
                " (SELECT to_jsonb(array_agg(x)) FROM"
                "  jsonb_array_elements_text(acoes) AS x WHERE x <> 'visualizar')"
                " WHERE perfil_id=%s AND recurso_id=%s",
                (pid[0], rid[0]),
            )
    finally:
        conn.autocommit = ac