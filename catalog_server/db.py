"""Banco de dados do servidor de catálogo.

- Catálogo (produtos/categorias/imagens): leitura somente-leitura do banco
  gerado pelo scraper (`database/crawler.db`).
- Sistema (fornecedores, cotações, preços, histórico): banco próprio em
  SQLite com modo WAL, para suportar vários usuários na rede local.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from catalog_server.config import CACHE_DB, SYSTEM_DB

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    razao_social TEXT DEFAULT '',
    cnpj_cpf TEXT DEFAULT '',
    representante TEXT DEFAULT '',
    whatsapp TEXT,
    email TEXT,
    observacoes TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Uma cotação é uma rodada de solicitação de preços (RFQ) para 1+ fornecedores.
CREATE TABLE IF NOT EXISTS cotacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    titulo TEXT,
    cliente TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'aberta',  -- aberta | fechada | cancelada | pendente | analise | finalizada
    observacoes TEXT,
    data_limite_retorno TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    fechado_em TEXT
);

-- Fornecedores convidados a responder uma cotação específica.
CREATE TABLE IF NOT EXISTS cotacao_fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    status TEXT NOT NULL DEFAULT 'pendente',  -- pendente | respondido
    token TEXT UNIQUE,
    data_resposta TEXT,
    UNIQUE(cotacao_id, fornecedor_id)
);

-- Itens (produto + quantidade desejada) que compõem a cotação.
CREATE TABLE IF NOT EXISTS cotacao_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    UNIQUE(cotacao_id, produto_id)
);

-- Preço informado por CADA fornecedor para CADA item, com timestamp próprio.
-- Consultar essas linhas por produto ao longo do tempo é o histórico de preços.
CREATE TABLE IF NOT EXISTS cotacao_precos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_item_id INTEGER NOT NULL REFERENCES cotacao_itens(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    preco_unitario REAL NOT NULL,
    desconto_percentual REAL,
    prazo_entrega_dias INTEGER,
    disponibilidade_estoque INTEGER NOT NULL DEFAULT 1,
    observacao TEXT,
    registrado_em TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(cotacao_item_id, fornecedor_id)
);

-- Pedido de compra consolidado por fornecedor (gerado no fechamento de uma
-- cotação). Status: enviado | faturado.
CREATE TABLE IF NOT EXISTS pedidos_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    status TEXT NOT NULL DEFAULT 'enviado',
    observacoes TEXT,
    data_geracao TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Registrado quando a cotação é fechada: quem venceu cada item.
CREATE TABLE IF NOT EXISTS pedido_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    cotacao_item_id INTEGER NOT NULL REFERENCES cotacao_itens(id),
    pedido_id INTEGER REFERENCES pedidos_compra(id) ON DELETE SET NULL,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    preco_unitario REAL NOT NULL,
    quantidade REAL NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- Cadastro de produtos (modelo TOTVS: Família -> Características -> Opções)
-- ---------------------------------------------------------------------

-- Família/grupo de produto (ex.: "Cabo Flexível", "Parafuso", "Cola").
CREATE TABLE IF NOT EXISTS familias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT DEFAULT '',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Características/atributos da família (SBQ). tipo: 'lista' (opções fixas)
-- ou 'livre' (valor digitado). opcoes é um JSON array de strings.
CREATE TABLE IF NOT EXISTS familia_atributos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'lista',
    opcoes TEXT DEFAULT '[]',
    obrigatorio INTEGER NOT NULL DEFAULT 0,
    ordem INTEGER NOT NULL DEFAULT 0,
    UNIQUE(familia_id, nome)
);

-- Taxonomia normalizada: categoria e subcategoria viram tabelas com FK.
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS subcategorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    UNIQUE(categoria_id, nome)
);

-- Produto cadastrado (pai): nome base, marca, categoria e descrição.
CREATE TABLE IF NOT EXISTS produtos_cadastro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    familia_id INTEGER NOT NULL REFERENCES familias(id),
    nome TEXT NOT NULL,
    marca TEXT DEFAULT '',
    descricao TEXT DEFAULT '',
    categoria_id INTEGER REFERENCES categorias(id),
    subcategoria_id INTEGER REFERENCES subcategorias(id),
    termos_busca TEXT DEFAULT '',
    embalagem TEXT DEFAULT '',
    url TEXT DEFAULT '',
    external_id INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT
);

-- Variação/SKU do produto (uma combinação de valores dos atributos).
CREATE TABLE IF NOT EXISTS variantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos_cadastro(id) ON DELETE CASCADE,
    sku TEXT DEFAULT '',
    ean TEXT DEFAULT '',
    preco REAL NOT NULL DEFAULT 0,
    preco_promocional REAL,
    old_price REAL,
    pix_price REAL,
    installment TEXT DEFAULT '',
    url TEXT DEFAULT '',
    external_id INTEGER,
    marca TEXT DEFAULT '',
    observacao TEXT DEFAULT '',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Valor de cada atributo em cada variante.
CREATE TABLE IF NOT EXISTS variante_atributos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id INTEGER NOT NULL REFERENCES variantes(id) ON DELETE CASCADE,
    atributo_id INTEGER NOT NULL REFERENCES familia_atributos(id) ON DELETE CASCADE,
    valor TEXT NOT NULL,
    UNIQUE(variante_id, atributo_id)
);

-- Imagens dos produtos cadastrados (podem ser específicas de uma variante).
CREATE TABLE IF NOT EXISTS imagens_produto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos_cadastro(id) ON DELETE CASCADE,
    variante_id INTEGER REFERENCES variantes(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    url_origem TEXT DEFAULT '',
    ordem INTEGER NOT NULL DEFAULT 0
);

-- Códigos do fornecedor para cada variante (compra): código, unidade de
-- compra e fator de conversão (ex.: embalagem com 10 unidades -> fator 10).
CREATE TABLE IF NOT EXISTS fornecedor_variantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id INTEGER NOT NULL REFERENCES variantes(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    codigo_fornecedor TEXT DEFAULT '',
    descricao_fornecedor TEXT DEFAULT '',
    unidade_compra TEXT DEFAULT '',
    fator_conversao REAL NOT NULL DEFAULT 1,
    UNIQUE(variante_id, fornecedor_id)
);

-- Marcadores de migração do scraper (base única).
CREATE TABLE IF NOT EXISTS scraper_sync (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cotacao_remap_done INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT
);

-- Índice das páginas-fonte (HTML) salvas no próprio banco, para consultas
-- futuras sem rebaixar a página (breadcrumb, preços, dados).
CREATE TABLE IF NOT EXISTS paginas_fonte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    site TEXT DEFAULT '',
    html TEXT,
    bytes INTEGER DEFAULT 0,
    url_final TEXT DEFAULT '',
    produto_id INTEGER,
    variante_id INTEGER,
    origem TEXT DEFAULT '',
    criada_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizada_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_site ON paginas_fonte(site);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_produto ON paginas_fonte(produto_id);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_variante ON paginas_fonte(variante_id);
"""

# ---------------------------------------------------------------------------
# Cache de páginas-fonte em BANCO SEPARADO (server_cache.db)
# ---------------------------------------------------------------------------
# O HTML cru das páginas baixadas é volumoso (centenas de KB por página).
# Mantê-lo no mesmo arquivo do catálogo/ERP infla o DB e degrada o
# desempenho das consultas — por isso ele fica num banco dedicado.
CACHE_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS paginas_fonte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    site TEXT DEFAULT '',
    html TEXT,
    bytes INTEGER DEFAULT 0,
    url_final TEXT DEFAULT '',
    produto_id INTEGER,
    variante_id INTEGER,
    origem TEXT DEFAULT '',
    criada_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizada_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_site ON paginas_fonte(site);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_produto ON paginas_fonte(produto_id);
CREATE INDEX IF NOT EXISTS idx_paginas_fonte_variante ON paginas_fonte(variante_id);
"""


def init_cache_db() -> None:
    """Cria o banco de cache de páginas-fonte se necessário."""
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.executescript(CACHE_SCHEMA)
    conn.commit()
    conn.close()


@contextmanager
def cache_conn():
    """Conexão com o banco de cache de páginas-fonte (separado do catálogo)."""
    init_cache_db()
    conn = sqlite3.connect(CACHE_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = SYSTEM_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.isolation_level = None  # autocommit: o script de migração controla BEGIN/COMMIT
    conn.executescript(SCHEMA)
    migrated = False
    if _has_legacy_taxonomy(conn):
        _migrate_legacy_taxonomy(conn)
        migrated = True
    ensure_schema(conn)
    from catalog_server import fts
    if migrated:
        # O FTS antigo (sem termos_busca) precisa ser recriado do zero.
        conn.execute("DROP TABLE IF EXISTS produtos_fts")
    fts.ensure_fts(conn)
    conn.commit()
    conn.close()


def _has_legacy_taxonomy(conn: sqlite3.Connection) -> bool:
    """Verdadeiro se produtos_cadastro ainda usa as colunas de texto (legado)."""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(produtos_cadastro)").fetchall()}
    except sqlite3.OperationalError:
        return False
    return "categoria" in cols and "subcategoria" in cols


def _migrate_legacy_taxonomy(conn: sqlite3.Connection) -> None:
    """Converte o schema antigo (categoria/subcategoria TEXT) para a taxonomia
    normalizada (categorias/subcategorias + FKs) usando a técnica de 12 passos.

    Idempotente: ao término as colunas de texto somem, então a função não roda
    de novo no próximo boot. Como `PRAGMA foreign_keys` é no-op dentro de uma
    transação, ele é alternado FORA do BEGIN/COMMIT.
    """
    # Povoa a taxonomia antes de reconstruir (categoria -> subcategorias).
    conn.execute(
        "INSERT OR IGNORE INTO categorias (nome, ativo) "
        "SELECT TRIM(categoria), 1 FROM produtos_cadastro "
        "WHERE categoria IS NOT NULL AND TRIM(categoria) <> '' "
        "GROUP BY TRIM(categoria)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO subcategorias (categoria_id, nome, ativo) "
        "SELECT c.id, TRIM(p.subcategoria), 1 "
        "FROM (SELECT DISTINCT categoria, subcategoria FROM produtos_cadastro "
        "      WHERE subcategoria IS NOT NULL AND TRIM(subcategoria) <> '') p "
        "JOIN categorias c ON c.nome = TRIM(p.categoria) "
        "GROUP BY c.id, TRIM(p.subcategoria)"
    )

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        conn.execute("""
            CREATE TABLE produtos_cadastro_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                familia_id INTEGER NOT NULL REFERENCES familias(id),
                nome TEXT NOT NULL,
                marca TEXT DEFAULT '',
                descricao TEXT DEFAULT '',
                categoria_id INTEGER REFERENCES categorias(id),
                subcategoria_id INTEGER REFERENCES subcategorias(id),
                termos_busca TEXT DEFAULT '',
                embalagem TEXT DEFAULT '',
                url TEXT DEFAULT '',
                external_id INTEGER,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                atualizado_em TEXT,
                linha_produto TEXT DEFAULT '',
                classe_abc TEXT DEFAULT '',
                ordem_abc INTEGER DEFAULT 0,
                margem_lucro_estimada REAL,
                giro_esperado_mercado REAL,
                valor_agregado TEXT DEFAULT '',
                lucro_total_estimado REAL,
                em_linha INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            INSERT INTO produtos_cadastro_new (
                id, familia_id, nome, marca, descricao, embalagem, url,
                external_id, ativo, criado_em, atualizado_em, linha_produto,
                classe_abc, ordem_abc, margem_lucro_estimada,
                giro_esperado_mercado, valor_agregado, lucro_total_estimado,
                em_linha, categoria_id, subcategoria_id, termos_busca
            )
            SELECT p.id, p.familia_id, p.nome, p.marca, p.descricao, p.embalagem,
                   p.url, p.external_id, p.ativo, p.criado_em, p.atualizado_em,
                   p.linha_produto, p.classe_abc, p.ordem_abc,
                   p.margem_lucro_estimada, p.giro_esperado_mercado,
                   p.valor_agregado, p.lucro_total_estimado, p.em_linha,
                   c.id, sc.id, ''
            FROM produtos_cadastro p
            LEFT JOIN categorias c ON c.nome = TRIM(p.categoria)
            LEFT JOIN subcategorias sc ON sc.nome = TRIM(p.subcategoria)
                                     AND sc.categoria_id = c.id
        """)
        conn.execute("DROP TABLE produtos_cadastro")
        conn.execute("ALTER TABLE produtos_cadastro_new RENAME TO produtos_cadastro")
        conn.execute("PRAGMA foreign_key_check")
        conn.execute("COMMIT")
    except sqlite3.Error:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


# Colunas adicionadas depois do schema inicial (migração de bancos existentes).
_SCHEMA_ADD = {
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


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Adiciona colunas novas em bancos criados com schema anterior."""
    for table, cols in _SCHEMA_ADD.items():
        try:
            existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        except sqlite3.OperationalError:
            continue
        for name, ddl in cols.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
    _ensure_indexes(conn)


# Índices para acelerar listagem, busca e montagem de cards. Sem eles, as
# subqueries correlacionadas varrem a tabela inteira para cada produto.
_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos_cadastro(nome COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_familia ON produtos_cadastro(familia_id)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_categoria_id ON produtos_cadastro(categoria_id)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_subcategoria_id ON produtos_cadastro(subcategoria_id)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_linha ON produtos_cadastro(linha_produto)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_classe_abc ON produtos_cadastro(classe_abc)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_ordem_abc ON produtos_cadastro(ordem_abc)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_em_linha ON produtos_cadastro(em_linha)",
    "CREATE INDEX IF NOT EXISTS idx_produtos_ativo ON produtos_cadastro(ativo)",
    "CREATE INDEX IF NOT EXISTS idx_variantes_produto ON variantes(produto_id)",
    "CREATE INDEX IF NOT EXISTS idx_variantes_produto_ativo ON variantes(produto_id, ativo)",
    "CREATE INDEX IF NOT EXISTS idx_imagens_produto_produto ON imagens_produto(produto_id)",
    "CREATE INDEX IF NOT EXISTS idx_variante_atributos_variante ON variante_atributos(variante_id)",
    "CREATE INDEX IF NOT EXISTS idx_variante_atributos_atributo ON variante_atributos(atributo_id)",
    "CREATE INDEX IF NOT EXISTS idx_familia_atributos_familia ON familia_atributos(familia_id)",
]


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    # Índice antigo (coluna única) que confundia o planejador e gerava varreduras
    # gigantes nas subqueries correlacionadas — removido em favor do composto.
    conn.execute("DROP INDEX IF EXISTS idx_variantes_ativo")
    for ddl in _INDEXES:
        conn.execute(ddl)


@contextmanager
def system_conn():
    """Conexão com o banco próprio do módulo (fornecedores/cotações)."""
    init_db()
    conn = sqlite3.connect(SYSTEM_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def next_cotacao_numero(conn) -> str:
    row = conn.execute("SELECT COUNT(*) AS n FROM cotacoes").fetchone()
    return str(row["n"] + 1).zfill(4)
