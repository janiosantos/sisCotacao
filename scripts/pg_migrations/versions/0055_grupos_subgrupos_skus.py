"""Migração 0055 — Grupos/subgrupos, códigos e SKU estruturado.

Adiciona a taxonomia de **grupo/subgrupo** ao cadastro de produtos e os
**códigos** curtos usados na composição do SKU estruturado
`[GRUPO]-[SUBGRUPO]-[MARCA]-[ATRIBUTOS]`:

1. Tabela `grupos` (codigo, nome) — ex.: ELE/ELETRICO, HID/HIDRAULICO,
   FER/FERRAMENTAS, PAR/PARAFUSOS.
2. Tabela `subgrupos` (grupo_id, codigo, nome) — ex.: CAB/Cabos, TUB/Tubos.
3. Colunas `grupo_id`/`subgrupo_id` em `produtos_cadastro` (FKs opcionais).
4. Coluna `codigo` em `marcas`, `categorias` e `subcategorias` (abreviação
   manual mantida pelo operador).
5. Seed dos grupos de exemplo citados pelo usuário.

O SKU em si é gerado pelo `sku_service` a partir destes códigos; esta
migração apenas disponibiliza os dados.

`backward`: remove colunas/tabelas novas (preservando os dados de produtos).
"""
from __future__ import annotations

VERSION = 55
NAME = "grupos_subgrupos_skus"

_GRUPOS_SEED = [
    ("ELE", "ELETRICO"),
    ("HID", "HIDRAULICO"),
    ("FER", "FERRAMENTAS"),
    ("PAR", "PARAFUSOS"),
]


def guard(conn) -> bool:
    # Estado-alvo final: tabelas criadas, FKs presentes e seed de grupos aplicado.
    row = conn.execute(
        "SELECT 1 FROM grupos WHERE codigo='ELE'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS grupos (
                id      BIGSERIAL PRIMARY KEY,
                codigo  TEXT NOT NULL UNIQUE,
                nome    TEXT NOT NULL,
                ativo   INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subgrupos (
                id         BIGSERIAL PRIMARY KEY,
                grupo_id   INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
                codigo     TEXT NOT NULL,
                nome       TEXT NOT NULL,
                ativo      INTEGER NOT NULL DEFAULT 1,
                UNIQUE(grupo_id, codigo),
                UNIQUE(grupo_id, nome)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_subgrupos_grupo"
            " ON subgrupos(grupo_id)"
        )

        conn.execute(
            "ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS grupo_id INTEGER"
        )
        conn.execute(
            "ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS subgrupo_id INTEGER"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_produtos_grupo_id"
            " ON produtos_cadastro(grupo_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_produtos_subgrupo_id"
            " ON produtos_cadastro(subgrupo_id)"
        )
        conn.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name='fk_produtos_cadastro_grupo_id'
                ) THEN
                    ALTER TABLE produtos_cadastro
                        ADD CONSTRAINT fk_produtos_cadastro_grupo_id
                        FOREIGN KEY (grupo_id) REFERENCES grupos(id);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name='fk_produtos_cadastro_subgrupo_id'
                ) THEN
                    ALTER TABLE produtos_cadastro
                        ADD CONSTRAINT fk_produtos_cadastro_subgrupo_id
                        FOREIGN KEY (subgrupo_id) REFERENCES subgrupos(id);
                END IF;
            END $$;
            """
        )

        conn.execute("ALTER TABLE marcas ADD COLUMN IF NOT EXISTS codigo TEXT")
        conn.execute("ALTER TABLE categorias ADD COLUMN IF NOT EXISTS codigo TEXT")
        conn.execute("ALTER TABLE subcategorias ADD COLUMN IF NOT EXISTS codigo TEXT")

        for codigo, nome in _GRUPOS_SEED:
            conn.execute(
                "INSERT INTO grupos (codigo, nome, ativo) VALUES (%s, %s, 1)"
                " ON CONFLICT (codigo) DO NOTHING",
                (codigo, nome),
            )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS subgrupo_id"
        )
        conn.execute(
            "ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS grupo_id"
        )
        conn.execute("ALTER TABLE subcategorias DROP COLUMN IF EXISTS codigo")
        conn.execute("ALTER TABLE categorias DROP COLUMN IF EXISTS codigo")
        conn.execute("ALTER TABLE marcas DROP COLUMN IF EXISTS codigo")
        conn.execute("DROP TABLE IF EXISTS subgrupos")
        conn.execute("DROP TABLE IF EXISTS grupos")
    finally:
        conn.autocommit = autocommit
