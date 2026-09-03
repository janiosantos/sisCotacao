"""Migração 0152 — preserva o método das tabelas antigas de preço."""
from __future__ import annotations

VERSION = 152
RISCO = "rotina"
NAME = "preserva_markup_legado"

MUDANCA = {
    "o_que": ["Marca como markup sobre o custo as tabelas antigas sem margem que já tinham markup"],
    "porque": ["Evitar alteração silenciosa de preços publicados na adoção do método divisor"],
}


def guard(conn) -> bool:
    return not bool(conn.execute(
        "SELECT 1 FROM tabelas_preco "
        "WHERE metodologia='markup_custo' AND COALESCE(markup, 0) > 0 "
        "AND COALESCE(margem_padrao, 0) = 0 LIMIT 1"
    ).fetchone())


def forward(conn) -> None:
    conn.execute(
        "UPDATE tabelas_preco SET metodologia='markup_custo' "
        "WHERE metodologia='divisor' AND COALESCE(markup, 0) > 0 "
        "AND COALESCE(margem_padrao, 0) = 0"
    )
    conn.commit()


def backward(conn) -> None:
    # O valor anterior não é distinguível de uma tabela nova; o rollback
    # estrutural continua seguro e a escolha do método pode ser feita na UI.
    conn.commit()
