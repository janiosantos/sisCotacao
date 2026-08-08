"""0002 — Colunas adicionadas depois do schema inicial (_SCHEMA_ADD).

Idempotente: cada `ALTER TABLE ADD COLUMN` só roda se a coluna não existe.
Bancos criados pelo baseline (0001) já têm todas essas colunas; a guarda
retorna True e nada é re-executado.
"""
from __future__ import annotations

import sqlite3

VERSION = 2
NAME = "colunas adicionais pós-baseline (_SCHEMA_ADD)"

_SCHEMA_ADD: dict[str, dict[str, str]] = {
    "produtos_cadastro": {
        "embalagem": "TEXT DEFAULT ''",
        "url": "TEXT DEFAULT ''",
        "external_id": "INTEGER",
        "linha_produto": "TEXT DEFAULT ''",
        "classe_abc": "TEXT DEFAULT ''",
        "ordem_abc": "INTEGER DEFAULT 0",
        "margem_lucro_estimada": "REAL",
        "giro_esperado_mercado": "REAL",
        "valor_agregado": "TEXT DEFAULT ''",
        "lucro_total_estimado": "REAL",
        "em_linha": "INTEGER DEFAULT 1",
        "categoria_id": "INTEGER",
        "subcategoria_id": "INTEGER",
        "termos_busca": "TEXT DEFAULT ''",
    },
    "variantes": {
        "old_price": "REAL",
        "pix_price": "REAL",
        "installment": "TEXT DEFAULT ''",
        "url": "TEXT DEFAULT ''",
        "external_id": "INTEGER",
        "marca": "TEXT DEFAULT ''",
        "custo_unitario": "REAL",
        "preco_venda": "REAL",
    },
    "cotacao_precos": {
        "validade_preco_em": "TEXT",
        "desconto_percentual": "REAL",
        "disponibilidade_estoque": "INTEGER NOT NULL DEFAULT 1",
    },
    "cotacoes": {
        "data_limite_retorno": "TEXT",
    },
    "cotacao_fornecedores": {
        "token": "TEXT",
        "data_resposta": "TEXT",
    },
    "fornecedores": {
        "razao_social": "TEXT DEFAULT ''",
        "cnpj_cpf": "TEXT DEFAULT ''",
        "representante": "TEXT DEFAULT ''",
    },
    "pedido_itens": {
        "pedido_id": "INTEGER",
    },
    "familia_atributos": {
        "obrigatorio": "INTEGER NOT NULL DEFAULT 0",
    },
}


def guard(conn: sqlite3.Connection) -> bool:
    """True se todas as colunas do mapa já existirem nas tabelas presentes."""
    restantes = 0
    for table, cols in _SCHEMA_ADD.items():
        try:
            existing = {
                r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
        except sqlite3.OperationalError:
            # tabela ainda não criada (na ordem de migração isso não ocorre)
            return False
        for name in cols:
            if name not in existing:
                restantes += 1
    return restantes == 0


def forward(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        for table, cols in _SCHEMA_ADD.items():
            try:
                existing = {
                    r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
                }
            except sqlite3.OperationalError:
                continue
            for name, ddl in cols.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
