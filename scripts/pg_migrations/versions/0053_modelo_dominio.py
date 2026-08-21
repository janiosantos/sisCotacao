"""Migração 0053 — Modelo de domínio (Sprint 1).

Aplica, de forma incremental e reversível sobre o baseline 0052:

1. **Desacoplamento do scraper**: faz backup das tabelas do scraper
   (`products`, `product_attributes`, `images`, `categories`, `crawler_state`)
   em tabelas `_backup_*` e as remove do banco do ERP. O scraper passa a
   exportar o catálogo em arquivo JSON (não grava mais aqui).
2. **Marcas**: cria a tabela `marcas` e vincula `produtos_cadastro.marca_id`
   (backfill a partir das marcas textuais existentes).
3. **Atributos JSONB**: adiciona `variantes.atributos JSONB` e faz backfill a
   partir do EAV (`variante_atributos` + `familia_atributos`). O EAV continua
   sendo mantido em paralelo até a limpeza final (Sprint 9).
4. **SKU único**: gera SKU para vazios, resolve duplicados e cria índice único
   parcial (SKU preenchido nunca repete).

Rollback (`backward`): recria as tabelas do scraper a partir dos backups e
remove as colunas/tabelas novas.
"""
from __future__ import annotations

VERSION = 53
RISCO = "critica"
NAME = "modelo_dominio"

# Tabelas do scraper que saem do banco do ERP (backup em _backup_*).
_SCRAPER_TABLES = [
    "product_attributes",
    "images",
    "categories",
    "crawler_state",
    "products",
]


def guard(conn) -> bool:
    """Já aplicada se o índice único de SKU existir (último passo da migração)."""
    row = conn.execute(
        "SELECT 1 FROM pg_indexes"
        " WHERE schemaname='public' AND indexname='idx_variantes_sku_unique'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        # 1. Backup + drop das tabelas do scraper (ordem: dependências antes).
        for t in _SCRAPER_TABLES:
            exists = conn.execute(
                "SELECT 1 FROM information_schema.tables"
                " WHERE table_schema='public' AND table_name=%s",
                (t,),
            ).fetchone()
            if not exists:
                continue
            conn.execute(f'CREATE TABLE IF NOT EXISTS "_backup_{t}" AS SELECT * FROM {t}')
            conn.execute(f"DROP TABLE {t}")

        # 2. Marcas.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS marcas (
                id      BIGSERIAL PRIMARY KEY,
                nome    TEXT NOT NULL UNIQUE,
                ativo   INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            INSERT INTO marcas (nome)
            SELECT DISTINCT TRIM(marca) FROM produtos_cadastro
            WHERE TRIM(marca) <> ''
            ON CONFLICT (nome) DO NOTHING
        """)
        conn.execute("""
            ALTER TABLE produtos_cadastro
            ADD COLUMN IF NOT EXISTS marca_id INTEGER REFERENCES marcas(id)
        """)
        conn.execute("""
            UPDATE produtos_cadastro p SET marca_id = m.id
            FROM marcas m
            WHERE TRIM(p.marca) = m.nome AND p.marca_id IS NULL
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_produtos_marca_id"
            " ON produtos_cadastro(marca_id)"
        )

        # 3. Atributos JSONB na variante (+ backfill do EAV).
        conn.execute("""
            ALTER TABLE variantes
            ADD COLUMN IF NOT EXISTS atributos JSONB NOT NULL DEFAULT '{}'
        """)
        conn.execute("""
            UPDATE variantes v SET atributos = COALESCE((
                SELECT jsonb_object_agg(fa.nome, va.valor)
                FROM variante_atributos va
                JOIN familia_atributos fa ON fa.id = va.atributo_id
                WHERE va.variante_id = v.id
            ), '{}'::jsonb)
            WHERE v.atributos = '{}'::jsonb
        """)

        # 4. SKU: backfill de vazios + resolução de duplicados + índice único.
        conn.execute("""
            UPDATE variantes
            SET sku = 'SKU-' || produto_id || '-' || id
            WHERE sku IS NULL OR TRIM(sku) = ''
        """)
        # Mantém o menor id de cada grupo de SKU duplicado e sufixa os demais
        # com `-N`; repete até não sobrar duplicado (sufixos podem colidir com
        # SKUs já existentes, por isso o loop em vez de uma única passada).
        # Índice temporário em `sku` para a subquery correlacionada não virar
        # O(n²).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS tmp_idx_variantes_sku ON variantes(sku)"
        )
        try:
            while True:
                dup = conn.execute(
                    "SELECT 1 FROM variantes WHERE sku <> ''"
                    " GROUP BY sku HAVING COUNT(*) > 1 LIMIT 1"
                ).fetchone()
                if not dup:
                    break
                conn.execute("""
                    UPDATE variantes v SET sku = v.sku || '-' || (
                        SELECT COUNT(*) FROM variantes v2
                        WHERE v2.sku = v.sku AND v2.id < v.id
                    )
                    WHERE v.sku <> '' AND v.id NOT IN (
                        SELECT MIN(id) FROM variantes
                        WHERE sku <> '' GROUP BY sku HAVING COUNT(*) > 1
                    )
                """)
        finally:
            conn.execute("DROP INDEX IF EXISTS tmp_idx_variantes_sku")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_variantes_sku_unique"
            " ON variantes(sku) WHERE sku <> ''"
        )
    finally:
        conn.autocommit = autocommit


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP INDEX IF EXISTS idx_variantes_sku_unique")
        conn.execute("ALTER TABLE variantes DROP COLUMN IF EXISTS atributos")
        conn.execute("DROP INDEX IF EXISTS idx_produtos_marca_id")
        conn.execute("ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS marca_id")
        conn.execute("DROP TABLE IF EXISTS marcas")

        # Restaura as tabelas do scraper a partir dos backups (ordem reversa).
        for t in reversed(_SCRAPER_TABLES):
            exists = conn.execute(
                "SELECT 1 FROM information_schema.tables"
                " WHERE table_schema='public' AND table_name=%s",
                (t,),
            ).fetchone()
            if exists:
                continue
            conn.execute(f'CREATE TABLE IF NOT EXISTS {t} AS SELECT * FROM "_backup_{t}"')
    finally:
        conn.autocommit = autocommit
