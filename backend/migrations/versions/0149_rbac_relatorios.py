"""Migração 0149 — catálogo RBAC para relatórios.

O frontend usa ``relatorios`` como recurso da rota, mas o catálogo original
possuía apenas ``dashboard``. A separação permite controlar a central analítica
sem confundir o painel operacional.
"""
from __future__ import annotations

VERSION = 149
RISCO = "rotina"
NAME = "rbac_relatorios"

MUDANCA = {
    "o_que": ["Adiciona o recurso relatorios ao catálogo RBAC"],
    "porque": ["Alinha o gate da rota e dos endpoints de relatórios ao contrato do frontend"],
}


def guard(conn) -> bool:
    return bool(conn.execute("SELECT 1 FROM recursos WHERE codigo='relatorios'").fetchone())


def forward(conn) -> None:
    conn.execute(
        "INSERT INTO recursos (codigo, nome, grupo) VALUES (%s, %s, %s) "
        "ON CONFLICT (codigo) DO UPDATE SET nome=EXCLUDED.nome, grupo=EXCLUDED.grupo, ativo=1",
        ("relatorios", "Relatórios", "Administração"),
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DELETE FROM recursos WHERE codigo='relatorios'")
    conn.commit()

