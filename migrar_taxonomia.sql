-- ============================================================================
-- MIGRAÇÃO / REFATORAÇÃO DE SCHEMA — catálogo ERP/B2B (SQLite)
-- Alvo: amostra_estrutura.db
--
-- Passo 1 : Normalização da taxonomia (categorias/subcategorias)
-- Passo 2 : Sinônimos de busca (termos_busca) + rebuild do FTS5
-- Passo 3 : Vínculo comercial (SKU do fornecedor x variante interna)
-- Passo 4 : Controle de validade nas cotações
--
-- IMPORTANTE (SQLite): PRAGMA foreign_keys está DESLIGADO durante a
-- reconstrução da tabela principal (Passo 1.4) e reativado ao final, porque
-- PRAGMA foreign_keys é operação de "no-op" dentro de uma transação — ele só
-- pode ser alternado fora delas. Toda a reconstrução fica dentro de uma única
-- transação (BEGIN/COMMIT) para que o banco nunca esteja em estado
-- intermediário (all-or-nothing).
-- ============================================================================


-- ----------------------------------------------------------------------------
-- PASSO 1.1 e 1.2 — CRIAR TABELAS DE TAXONOMIA
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categorias (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nome   TEXT    NOT NULL UNIQUE,
    ativo  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS subcategorias (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
    nome         TEXT    NOT NULL,
    ativo        INTEGER NOT NULL DEFAULT 1,
    UNIQUE (categoria_id, nome)
);


-- ----------------------------------------------------------------------------
-- PASSO 1.3 — PLANO DE MIGRAÇÃO DE DADOS
-- Extrai os valores distintos de categoria e subcategoria de produtos_cadastro
-- e insere em categorias/subcategorias. Como a granularidade mais fina é a
-- subcategoria (que NÃO é globalmente única), o vínculo é feito a partir do
-- par (categoria, subcategoria).
-- ----------------------------------------------------------------------------
-- Categorias:
INSERT OR IGNORE INTO categorias (nome, ativo)
SELECT TRIM(categoria), 1 FROM produtos_cadastro
WHERE categoria IS NOT NULL AND TRIM(categoria) <> ''
GROUP BY TRIM(categoria);

-- Subcategorias (vínculo pela categoria correta, via nome):
INSERT OR IGNORE INTO subcategorias (categoria_id, nome, ativo)
SELECT c.id, TRIM(p.subcategoria), 1
FROM (SELECT DISTINCT categoria, subcategoria FROM produtos_cadastro
      WHERE subcategoria IS NOT NULL AND TRIM(subcategoria) <> '') p
JOIN categorias c ON c.nome = TRIM(p.categoria)
GROUP BY c.id, TRIM(p.subcategoria);


-- ----------------------------------------------------------------------------
-- PASSO 1.4 — RECONSTRUÇÃO DA TABELA PRINCIPAL (12-passos do SQLite)
-- Remove colunas de texto categoria/subcategoria e adiciona categoria_id e
-- subcategoria_id como FKs. Para isso usamos tabela temporária + rename.
-- Para datar as FKs, trocamos a verificação para a TÉCNICA DE 12 PASSOS:
--   foreign_keys=OFF (fora de txn) -> BEGIN -> ALTER/copy -> DROP -> RENAME
--   -> recria índices -> foreign_key_check -> COMMIT -> foreign_keys=ON
-- ----------------------------------------------------------------------------
PRAGMA foreign_keys = OFF;

BEGIN;

-- Cria a nova estrutura (mesmas colunas, sem textos de categoria, com FKs)
CREATE TABLE produtos_cadastro_new (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    familia_id               INTEGER NOT NULL REFERENCES familias(id),
    nome                     TEXT    NOT NULL,
    marca                    TEXT    DEFAULT '',
    descricao                TEXT    DEFAULT '',
    ativo                    INTEGER NOT NULL DEFAULT 1,
    criado_em                TEXT    NOT NULL DEFAULT (datetime('now')),
    atualizado_em            TEXT,
    embalagem                TEXT    DEFAULT '',
    url                      TEXT    DEFAULT '',
    external_id              INTEGER,
    linha_produto            TEXT    DEFAULT '',
    classe_abc               TEXT    DEFAULT '',
    ordem_abc                INTEGER DEFAULT 0,
    margem_lucro_estimada    REAL,
    giro_esperado_mercado    REAL,
    valor_agregado           TEXT    DEFAULT '',
    lucro_total_estimado     REAL,
    em_linha                 INTEGER DEFAULT 1,
    categoria_id             INTEGER REFERENCES categorias(id),
    subcategoria_id          INTEGER REFERENCES subcategorias(id)
);

-- Copia os dados, resolvendo as FKs pela taxa vigente (par categoria+subcat)
INSERT INTO produtos_cadastro_new (
    id, familia_id, nome, marca, descricao, ativo, criado_em, atualizado_em,
    embalagem, url, external_id, linha_produto, classe_abc, ordem_abc,
    margem_lucro_estimada, giro_esperado_mercado, valor_agregado,
    lucro_total_estimado, em_linha, categoria_id, subcategoria_id
)
SELECT
    p.id, p.familia_id, p.nome, p.marca, p.descricao, p.ativo, p.criado_em,
    p.atualizado_em, p.embalagem, p.url, p.external_id, p.linha_produto,
    p.classe_abc, p.ordem_abc, p.margem_lucro_estimada, p.giro_esperado_mercado,
    p.valor_agregado, p.lucro_total_estimado, p.em_linha,
    c.id, sc.id
FROM produtos_cadastro p
LEFT JOIN categorias c
       ON c.nome = TRIM(p.categoria)
LEFT JOIN subcategorias sc
       ON sc.nome = TRIM(p.subcategoria)
      AND sc.categoria_id = c.id;

-- Troca a tabela
DROP TABLE produtos_cadastro;
ALTER TABLE produtos_cadastro_new RENAME TO produtos_cadastro;

-- Recria os índices (os antigos categoria/subcategoria foram removidos junto
-- com a tabela; agora indexamos pelas FKs)
CREATE INDEX idx_produtos_ativo         ON produtos_cadastro(ativo);
CREATE INDEX idx_produtos_classe_abc    ON produtos_cadastro(classe_abc);
CREATE INDEX idx_produtos_em_linha      ON produtos_cadastro(em_linha);
CREATE INDEX idx_produtos_familia       ON produtos_cadastro(familia_id);
CREATE INDEX idx_produtos_linha         ON produtos_cadastro(linha_produto);
CREATE INDEX idx_produtos_nome          ON produtos_cadastro(nome COLLATE NOCASE);
CREATE INDEX idx_produtos_ordem_abc     ON produtos_cadastro(ordem_abc);
CREATE INDEX idx_produtos_categoria_id  ON produtos_cadastro(categoria_id);
CREATE INDEX idx_produtos_subcategoria_id ON produtos_cadastro(subcategoria_id);

-- Validação de integridade ANTES de commitar (a transação é descartada se falhar)
PRAGMA foreign_key_check;

COMMIT;

-- Restabelece a verificação de FKs (externo a transação)
PRAGMA foreign_keys = ON;


-- ----------------------------------------------------------------------------
-- PASSO 2.1 — ADICIONAR CAMPO DE SINÔNIMOS
-- Simples ALTER TABLE ADD COLUMN (SQLite não permite adicionar colunas com FK
-- via ALTER; como é apenas TEXT com default, é permitido).
-- ----------------------------------------------------------------------------
ALTER TABLE produtos_cadastro ADD COLUMN termos_busca TEXT DEFAULT '';


-- ----------------------------------------------------------------------------
-- PASSO 2.2 e 2.3 — RECRIAR O FTS5 INCLUINDO O NOVO CAMPO
-- Mantém exatamente a mesma tokenização e colunas, acrescentando termos_busca.
-- ----------------------------------------------------------------------------
DROP TABLE produtos_fts;

CREATE VIRTUAL TABLE produtos_fts USING fts5(
    produto_id UNINDEXED,
    nome,
    marca,
    descricao,
    familia,
    skus,
    termos_busca,
    tokenize='unicode61 remove_diacritics 2'
);

-- Reindexa os produtos (ex.: linha equivalente à usada pelo app no boot)
INSERT INTO produtos_fts (produto_id, nome, marca, descricao, familia, skus, termos_busca)
SELECT
    p.id,
    p.nome,
    COALESCE(p.marca, ''),
    COALESCE(p.descricao, ''),
    COALESCE(f.nome, ''),
    COALESCE((
        SELECT GROUP_CONCAT(v.sku, ' ')
          FROM variantes v WHERE v.produto_id = p.id), ''),
    COALESCE(p.termos_busca, '')
FROM produtos_cadastro p
LEFT JOIN familias f ON f.id = p.familia_id;


-- ----------------------------------------------------------------------------
-- PASSO 3 — VÍNCULO COMERCIAL: SKU DO FORNECEDOR x VARIANTE INTERNA
-- ----------------------------------------------------------------------------
CREATE TABLE fornecedor_variantes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    variante_id        INTEGER NOT NULL REFERENCES variantes(id) ON DELETE CASCADE,
    fornecedor_id      INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    codigo_fornecedor  TEXT    NOT NULL,
    descricao_fornecedor TEXT,
    unidade_compra     TEXT    DEFAULT 'UN',
    fator_conversao    REAL    DEFAULT 1,
    UNIQUE (variante_id, fornecedor_id)
);


-- ----------------------------------------------------------------------------
-- PASSO 4 — CONTROLE DE VALIDADE EM COTAÇÕES
-- ----------------------------------------------------------------------------
ALTER TABLE cotacao_precos ADD COLUMN validade_preco_em TEXT;


-- ============================================================================
-- VALIDAÇÃO FINAL — verifica que não ficou nada quebrado
-- ============================================================================
PRAGMA foreign_key_check;
SELECT 'categorias' AS tabela, COUNT(*) AS linhas FROM categorias
UNION ALL SELECT 'subcategorias', COUNT(*) FROM subcategorias
UNION ALL SELECT 'produtos_cadastro', COUNT(*) FROM produtos_cadastro
UNION ALL SELECT 'fornecedor_variantes', COUNT(*) FROM fornecedor_variantes;