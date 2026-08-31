"""Migração 0104 — ação fiscal de emissão para o perfil Operador."""
from __future__ import annotations

import json

VERSION = 104
RISCO = "moderada"
NAME = "rbac_emitir_fiscal_operador"

MUDANCA = {
    "o_que": ["Concede fiscal.emitir ao perfil Operador"],
    "porque": ["A emissão automática da NFC-e faz parte do fechamento do caixa"],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT pr.acoes FROM perfil_recurso pr "
        "JOIN perfis p ON p.id=pr.perfil_id "
        "JOIN recursos r ON r.id=pr.recurso_id "
        "WHERE p.nome=%s AND r.codigo=%s",
        ("Operador", "fiscal"),
    ).fetchone()
    if not row:
        return False
    acoes = row["acoes"] if isinstance(row, dict) else row[0]
    if isinstance(acoes, str):
        acoes = json.loads(acoes)
    return "emitir" in (acoes or [])


def forward(conn) -> None:
    row = conn.execute(
        "SELECT p.id AS perfil_id, r.id AS recurso_id, pr.acoes "
        "FROM perfis p CROSS JOIN recursos r "
        "LEFT JOIN perfil_recurso pr ON pr.perfil_id=p.id AND pr.recurso_id=r.id "
        "WHERE p.nome=%s AND r.codigo=%s",
        ("Operador", "fiscal"),
    ).fetchone()
    if not row:
        return
    acoes = row["acoes"] if isinstance(row, dict) else row[2]
    if isinstance(acoes, str):
        acoes = json.loads(acoes)
    acoes = list(dict.fromkeys([*(acoes or []), "emitir"]))
    perfil_id = row["perfil_id"] if isinstance(row, dict) else row[0]
    recurso_id = row["recurso_id"] if isinstance(row, dict) else row[1]
    conn.execute(
        "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes) VALUES (%s,%s,%s) "
        "ON CONFLICT (perfil_id, recurso_id) DO UPDATE SET acoes=EXCLUDED.acoes",
        (perfil_id, recurso_id, json.dumps(acoes)),
    )
    conn.commit()


def backward(conn) -> None:
    row = conn.execute(
        "SELECT p.id AS perfil_id, r.id AS recurso_id, pr.acoes "
        "FROM perfis p JOIN recursos r ON r.codigo=%s "
        "JOIN perfil_recurso pr ON pr.perfil_id=p.id AND pr.recurso_id=r.id "
        "WHERE p.nome=%s",
        ("fiscal", "Operador"),
    ).fetchone()
    if not row:
        return
    acoes = row["acoes"] if isinstance(row, dict) else row[2]
    if isinstance(acoes, str):
        acoes = json.loads(acoes)
    acoes = [a for a in (acoes or []) if a != "emitir"]
    perfil_id = row["perfil_id"] if isinstance(row, dict) else row[0]
    recurso_id = row["recurso_id"] if isinstance(row, dict) else row[1]
    conn.execute(
        "UPDATE perfil_recurso SET acoes=%s WHERE perfil_id=%s AND recurso_id=%s",
        (json.dumps(acoes), perfil_id, recurso_id),
    )
    conn.commit()
