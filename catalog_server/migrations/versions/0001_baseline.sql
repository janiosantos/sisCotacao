-- 0001_baseline
-- Schema original do catálogo/cotações (snapshot do db.SCHEMA). Idempotente:
-- todas as tabelas/índices usam IF NOT EXISTS, então rodar num banco antigo
-- é um no-op. Versões seguintes (0002+) aplicam evoluções pontuais.
PRAGMA foreign_keys = OFF;

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

CREATE TABLE IF NOT EXISTS cotacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    titulo TEXT,
    cliente TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'aberta',
    observacoes TEXT,
    data_limite_retorno TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    fechado_em TEXT
);

CREATE TABLE IF NOT EXISTS cotacao_fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    status TEXT NOT NULL DEFAULT 'pendente',
    token TEXT UNIQUE,
    data_resposta TEXT,
    UNIQUE(cotacao_id, fornecedor_id)
);

CREATE TABLE IF NOT EXISTS cotacao_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    UNIQUE(cotacao_id, produto_id)
);

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

CREATE TABLE IF NOT EXISTS familias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT DEFAULT '',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

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

CREATE TABLE IF NOT EXISTS variante_atributos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id INTEGER NOT NULL REFERENCES variantes(id) ON DELETE CASCADE,
    atributo_id INTEGER NOT NULL REFERENCES familia_atributos(id) ON DELETE CASCADE,
    valor TEXT NOT NULL,
    UNIQUE(variante_id, atributo_id)
);

CREATE TABLE IF NOT EXISTS imagens_produto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos_cadastro(id) ON DELETE CASCADE,
    variante_id INTEGER REFERENCES variantes(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    url_origem TEXT DEFAULT '',
    ordem INTEGER NOT NULL DEFAULT 0
);

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

CREATE TABLE IF NOT EXISTS scraper_sync (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cotacao_remap_done INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT
);

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

PRAGMA foreign_keys = ON;