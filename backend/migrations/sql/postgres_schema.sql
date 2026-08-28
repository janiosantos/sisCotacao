-- Schema PostgreSQL do ERP (catálogo/cotações/estoque/fiscal).
-- Referência aplicada pela migração baseline 0052.
-- Tabelas primeiro (sem FKs), índices, e FKs via ALTER TABLE ao final
-- para respeitar a ordem de criação no Postgres.

CREATE TABLE adiantamentos (
  id              BIGSERIAL PRIMARY KEY,
  tipo            TEXT NOT NULL CHECK(tipo IN ('cliente','fornecedor')),
  pessoa_id       INTEGER,
  pessoa_nome     TEXT NOT NULL,
  valor           DOUBLE PRECISION NOT NULL,
  saldo           DOUBLE PRECISION NOT NULL,
  data_adiantamento TEXT NOT NULL,
  data_baixa      TEXT,
  observacao      TEXT DEFAULT '',
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE beneficios_fiscais (
  id              BIGSERIAL PRIMARY KEY,
  codigo          TEXT NOT NULL UNIQUE,
  descricao       TEXT DEFAULT '',
  tipo            TEXT NOT NULL DEFAULT 'reducao_base'
                    CHECK(tipo IN ('isencao','reducao_base','credito_presumido','diferimento','suspensao')),
  valor_default   DOUBLE PRECISION DEFAULT 0,
  vigencia_inicio TEXT,
  vigencia_fim    TEXT,
  ativo           INTEGER NOT NULL DEFAULT 1,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE caixa_movimento (
  id                BIGSERIAL PRIMARY KEY,
  tipo              TEXT NOT NULL
                      CHECK(tipo IN ('abertura','entrada','saida','sangria','suprimento','fechamento')),
  descricao         TEXT NOT NULL DEFAULT '',
  valor             DOUBLE PRECISION NOT NULL,
  saldo_anterior    DOUBLE PRECISION NOT NULL DEFAULT 0,
  saldo_posterior   DOUBLE PRECISION NOT NULL DEFAULT 0,
  forma_pagamento   TEXT DEFAULT 'dinheiro',
  plano_conta_id    INTEGER ,
  documento         TEXT,
  orcamento_id      INTEGER ,
  usuario_id        INTEGER ,
  criado_em         TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  bandeira TEXT,
  codigo_autorizacao TEXT
);

CREATE TABLE categorias (
  id BIGSERIAL PRIMARY KEY,
  nome TEXT NOT NULL UNIQUE,
  codigo TEXT,
  ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE grupos (
  id BIGSERIAL PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  nome TEXT NOT NULL,
  ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE subgrupos (
  id BIGSERIAL PRIMARY KEY,
  grupo_id INTEGER NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
  codigo TEXT NOT NULL,
  nome TEXT NOT NULL,
  ativo INTEGER NOT NULL DEFAULT 1,
  UNIQUE(grupo_id, codigo),
  UNIQUE(grupo_id, nome)
);

CREATE TABLE centros_custo (
  id          BIGSERIAL PRIMARY KEY,
  codigo      TEXT NOT NULL UNIQUE,
  nome        TEXT NOT NULL,
  ativo       INTEGER NOT NULL DEFAULT 1,
  criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE cest (
  codigo          TEXT PRIMARY KEY,
  ncm_prefix      TEXT DEFAULT '',
  descricao       TEXT DEFAULT '',
  vigencia_inicio TEXT,
  vigencia_fim    TEXT,
  ativo           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE cfop (
  codigo    TEXT PRIMARY KEY,
  descricao TEXT NOT NULL,
  tipo      TEXT NOT NULL DEFAULT 'saida'
              CHECK(tipo IN ('entrada','saida','mesma_uf','outra_uf'))
);

CREATE TABLE cliente_apoio_comercial (
  id                   BIGSERIAL PRIMARY KEY,
  cliente_id           INTEGER NOT NULL UNIQUE,
  condicao_pagamento_id INTEGER,
  tabela_preco_id      INTEGER ,
  limite_credito       DOUBLE PRECISION DEFAULT 0,
  transportadora       TEXT DEFAULT '',
  criado_em            TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE cliente_apoio_fiscal (
  id             BIGSERIAL PRIMARY KEY,
  cliente_id     INTEGER NOT NULL UNIQUE,
  cfop_padrao    TEXT DEFAULT '',
  cst_icms       TEXT DEFAULT '',
  cst_pis        TEXT DEFAULT '',
  cst_cofins     TEXT DEFAULT '',
  aliquota_icms  DOUBLE PRECISION DEFAULT 0,
  aliquota_pis   DOUBLE PRECISION DEFAULT 0,
  aliquota_cofins DOUBLE PRECISION DEFAULT 0,
  criado_em      TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE cliente_contatos (
  id          BIGSERIAL PRIMARY KEY,
  cliente_id  INTEGER NOT NULL ,
  nome        TEXT NOT NULL,
  cargo       TEXT DEFAULT '',
  telefone    TEXT DEFAULT '',
  email       TEXT DEFAULT '',
  criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE cliente_enderecos (
  id          BIGSERIAL PRIMARY KEY,
  cliente_id  INTEGER NOT NULL ,
  tipo        TEXT NOT NULL CHECK(tipo IN ('cobranca','entrega','faturamento')),
  cep         TEXT DEFAULT '',
  logradouro  TEXT DEFAULT '',
  numero      TEXT DEFAULT '',
  complemento TEXT DEFAULT '',
  bairro      TEXT DEFAULT '',
  cidade      TEXT DEFAULT '',
  uf          TEXT DEFAULT '',
  criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE cliente_interacao (
  id                   BIGSERIAL PRIMARY KEY,
  cliente_id           INTEGER ,
  cliente_nome         TEXT NOT NULL,
  tipo                 TEXT NOT NULL
                         CHECK(tipo IN ('ligacao','visita','email','whatsapp','follow_up','outro')),
  descricao            TEXT NOT NULL DEFAULT '',
  data_contato         TEXT NOT NULL,
  data_proximo_contato TEXT,
  orcamento_id         INTEGER ,
  usuario_id           INTEGER ,
  criado_em            TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE clientes (
  id             BIGSERIAL PRIMARY KEY,
  nome           TEXT NOT NULL,
  tipo_pessoa    TEXT NOT NULL DEFAULT 'f',
  doc            TEXT,
  email          TEXT,
  telefone       TEXT,
  whatsapp       TEXT,
  endereco       TEXT,
  cidade         TEXT,
  uf             TEXT,
  cep            TEXT,
  vendedor_id    INTEGER ,
  limite_credito DOUBLE PRECISION NOT NULL DEFAULT 0,
  observacoes    TEXT,
  ativo          INTEGER NOT NULL DEFAULT 1,
  criado_em      TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em  TEXT,
  contribuinte TEXT DEFAULT '',
  ie TEXT DEFAULT '',
  c_municipio TEXT,
  numero TEXT,
  bairro TEXT,
  complemento TEXT
);

CREATE TABLE condicao_parcelas (
  id              BIGSERIAL PRIMARY KEY,
  condicao_id     INTEGER NOT NULL ,
  sequencia       INTEGER NOT NULL,
  dias            INTEGER NOT NULL DEFAULT 0,
  percentual      DOUBLE PRECISION NOT NULL DEFAULT 100,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE condicoes_pagamento (
  id          BIGSERIAL PRIMARY KEY,
  nome        TEXT NOT NULL,
  descricao   TEXT DEFAULT '',
  ativo       INTEGER NOT NULL DEFAULT 1,
  criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE config_loja (
  chave       TEXT PRIMARY KEY,
  valor       TEXT DEFAULT '',
  atualizado_em TEXT
);

CREATE TABLE contas_bancarias (
  id             BIGSERIAL PRIMARY KEY,
  nome           TEXT NOT NULL,
  banco          TEXT NOT NULL DEFAULT '000',
  agencia        TEXT DEFAULT '',
  conta          TEXT DEFAULT '',
  digito         TEXT DEFAULT '',
  saldo_inicial  DOUBLE PRECISION NOT NULL DEFAULT 0,
  saldo_atual    DOUBLE PRECISION NOT NULL DEFAULT 0,
  ativo          INTEGER NOT NULL DEFAULT 1,
  criado_em      TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE contas_pagar (
  id                BIGSERIAL PRIMARY KEY,
  fornecedor        TEXT NOT NULL DEFAULT '',
  fornecedor_id     INTEGER ,
  descricao         TEXT NOT NULL DEFAULT '',
  valor             DOUBLE PRECISION NOT NULL,
  saldo             DOUBLE PRECISION NOT NULL,
  data_vencimento   TEXT NOT NULL,
  data_emissao      TEXT NOT NULL DEFAULT (date('now')),
  data_pagamento    TEXT,
  plano_conta_id    INTEGER ,
  documento         TEXT,
  observacao        TEXT,
  status            TEXT NOT NULL DEFAULT 'aberto'
                      CHECK(status IN ('aberto','parcial','pago','cancelado')),
  criado_em         TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE contas_receber (
  id                BIGSERIAL PRIMARY KEY,
  cliente           TEXT NOT NULL DEFAULT '',
  cliente_id        INTEGER ,
  descricao         TEXT NOT NULL DEFAULT '',
  valor             DOUBLE PRECISION NOT NULL,
  saldo             DOUBLE PRECISION NOT NULL,
  data_vencimento   TEXT NOT NULL,
  data_emissao      TEXT NOT NULL DEFAULT (date('now')),
  data_recebimento  TEXT,
  plano_conta_id    INTEGER ,
  documento         TEXT,
  observacao        TEXT,
  status            TEXT NOT NULL DEFAULT 'aberto'
                      CHECK(status IN ('aberto','parcial','pago','cancelado')),
  criado_em         TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE cotacao_fornecedores (
  id BIGSERIAL PRIMARY KEY,
  cotacao_id INTEGER NOT NULL ,
  fornecedor_id INTEGER NOT NULL ,
  status TEXT NOT NULL DEFAULT 'pendente',
  token TEXT UNIQUE,
  data_resposta TEXT,
  condicao_pagamento TEXT,
  condicao_pagamento_dias INTEGER,
  UNIQUE(cotacao_id, fornecedor_id)
);

CREATE TABLE cotacao_itens (
  id BIGSERIAL PRIMARY KEY,
  cotacao_id INTEGER NOT NULL ,
  produto_id INTEGER,
  descricao TEXT NOT NULL DEFAULT '',
  quantidade DOUBLE PRECISION NOT NULL DEFAULT 1,
  UNIQUE(cotacao_id, produto_id)
);

CREATE TABLE cotacao_precos (
  id BIGSERIAL PRIMARY KEY,
  cotacao_item_id INTEGER NOT NULL ,
  fornecedor_id INTEGER NOT NULL ,
  preco_unitario DOUBLE PRECISION NOT NULL,
  desconto DOUBLE PRECISION,
  prazo_entrega_dias INTEGER,
  disponibilidade_estoque INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'aceito', 'recusado')),
  moeda TEXT NOT NULL DEFAULT 'BRL',
  observacao TEXT,
  registrado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  validade_preco_em TEXT,
  UNIQUE(cotacao_item_id, fornecedor_id)
);

CREATE TABLE cotacoes (
  id BIGSERIAL PRIMARY KEY,
  numero TEXT UNIQUE NOT NULL,
  titulo TEXT,
  cliente TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'aberta',
  observacoes TEXT,
  data_limite_retorno TEXT,
  criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  fechado_em TEXT
);

CREATE TABLE csosn (
  codigo    TEXT PRIMARY KEY,
  descricao TEXT NOT NULL
);

CREATE TABLE cst_cofins (
  codigo    TEXT PRIMARY KEY,
  descricao TEXT NOT NULL
);

CREATE TABLE cst_icms (
  codigo    TEXT PRIMARY KEY,
  descricao TEXT NOT NULL
);

CREATE TABLE cst_pis (
  codigo    TEXT PRIMARY KEY,
  descricao TEXT NOT NULL
);

CREATE TABLE depositos (
  id         BIGSERIAL PRIMARY KEY,
  nome       TEXT NOT NULL UNIQUE,
  ativo      INTEGER NOT NULL DEFAULT 1,
  criado_em  TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  tipo TEXT DEFAULT 'proprio' CHECK(tipo IN ('proprio','terceiros','virtual')),
  localizacao_rua TEXT DEFAULT '',
  localizacao_prateleira TEXT DEFAULT '',
  localizacao_nivel TEXT DEFAULT '',
  localizacao_vão TEXT DEFAULT ''
);

CREATE TABLE devolucoes (
  id           BIGSERIAL PRIMARY KEY,
  orcamento_id INTEGER ,
  variante_id  INTEGER ,
  quantidade   DOUBLE PRECISION NOT NULL DEFAULT 1,
  motivo       TEXT DEFAULT '',
  tipo         TEXT NOT NULL DEFAULT 'devolucao'
                 CHECK(tipo IN ('devolucao','troca')),
  status       TEXT NOT NULL DEFAULT 'registrada'
                 CHECK(status IN ('registrada','estornada','trocada')),
  deposito_id  INTEGER NOT NULL DEFAULT 1,
  usuario_id   INTEGER ,
  criado_em    TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE documentos_fiscais (
  id                BIGSERIAL PRIMARY KEY,
  orcamento_id      INTEGER NOT NULL ,
  modelo            TEXT NOT NULL DEFAULT '65' CHECK(modelo IN ('55','65')),
  ambiente          TEXT NOT NULL DEFAULT 'homologacao' CHECK(ambiente IN ('homologacao','producao')),
  status            TEXT NOT NULL DEFAULT 'pendente'
                      CHECK(status IN ('pendente','processando','autorizado','rejeitado','cancelado','erro')),
  tecnospeed_id     TEXT,
  chave_acesso      TEXT,
  protocolo         TEXT,
  numero            INTEGER,
  serie             INTEGER,
  motivo            TEXT,
  xml_url           TEXT,
  danfe_url         TEXT,
  payload_enviado   TEXT,
  resposta_bruta    TEXT,
  criado_em         TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em     TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  UNIQUE(orcamento_id, modelo)
);

CREATE TABLE emitente (
  id                  BIGSERIAL PRIMARY KEY,
  razao_social        TEXT NOT NULL,
  nome_fantasia       TEXT DEFAULT '',
  cnpj                TEXT NOT NULL,
  ie                  TEXT DEFAULT '',
  im                  TEXT DEFAULT '',
  regime_tributario   TEXT DEFAULT 'simples_nacional'
                        CHECK(regime_tributario IN ('simples_nacional','lucro_presumido','lucro_real')),
  cnae_principal      TEXT DEFAULT '',
  cnae_secundario     TEXT DEFAULT '',
  logradouro          TEXT DEFAULT '',
  numero              TEXT DEFAULT '',
  bairro              TEXT DEFAULT '',
  cep                 TEXT DEFAULT '',
  municipio           TEXT DEFAULT '',
  uf                  TEXT DEFAULT '',
  token_focus         TEXT DEFAULT '',
  ambiente_focus      TEXT DEFAULT 'homologacao' CHECK(ambiente_focus IN ('homologacao','producao')),
  aliquota_icms       DOUBLE PRECISION DEFAULT 18,
  aliquota_pis        DOUBLE PRECISION DEFAULT 1.65,
  aliquota_cofins     DOUBLE PRECISION DEFAULT 7.6,
  aliquota_ipi        DOUBLE PRECISION DEFAULT 0,
  serie_nfe           INTEGER DEFAULT 1,
  proximo_numero_nfe  INTEGER DEFAULT 1,
  ativo               INTEGER NOT NULL DEFAULT 1,
  criado_em           TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  crt INTEGER DEFAULT 1,
  aliquota_ibs DOUBLE PRECISION DEFAULT 0,
  aliquota_cbs DOUBLE PRECISION DEFAULT 0,
  ibs_vigencia_inicio TEXT,
  ibs_vigencia_fim TEXT,
  cbs_vigencia_inicio TEXT,
  cbs_vigencia_fim TEXT,
  c_municipio TEXT
);

CREATE TABLE estoque_movimento (
  id               BIGSERIAL PRIMARY KEY,
  deposito_id      INTEGER NOT NULL ,
  variante_id      INTEGER NOT NULL ,
  tipo             TEXT NOT NULL CHECK(tipo IN ('entrada','saida','ajuste','transferencia','inventario')),
  quantidade       DOUBLE PRECISION NOT NULL,
  saldo_anterior   DOUBLE PRECISION NOT NULL DEFAULT 0,
  saldo_posterior  DOUBLE PRECISION NOT NULL DEFAULT 0,
  documento        TEXT,
  observacao       TEXT,
  lote_id          INTEGER ,
  usuario_id       INTEGER ,
  criado_em        TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE estoque_saldo (
  id             BIGSERIAL PRIMARY KEY,
  deposito_id    INTEGER NOT NULL ,
  variante_id    INTEGER NOT NULL ,
  quantidade     DOUBLE PRECISION NOT NULL DEFAULT 0,
  reserva        DOUBLE PRECISION NOT NULL DEFAULT 0,
  atualizado_em  TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  estoque_minimo DOUBLE PRECISION DEFAULT 0,
  estoque_maximo DOUBLE PRECISION DEFAULT 0,
  localizacao TEXT DEFAULT '',
  UNIQUE(deposito_id, variante_id)
);

CREATE TABLE expedicao (
  id              BIGSERIAL PRIMARY KEY,
  codigo          TEXT NOT NULL,
  deposito_id     INTEGER NOT NULL ,
  data_expedicao  TEXT NOT NULL DEFAULT (date('now')),
  status          TEXT NOT NULL DEFAULT 'pendente'
                    CHECK(status IN ('pendente','separando','conferido','carregado','finalizado')),
  transportadora  TEXT DEFAULT '',
  observacao      TEXT DEFAULT '',
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE expedicao_itens (
  id              BIGSERIAL PRIMARY KEY,
  expedicao_id    INTEGER NOT NULL ,
  orcamento_id    INTEGER ,
  variante_id     INTEGER NOT NULL ,
  quantidade      DOUBLE PRECISION NOT NULL,
  quantidade_sep  DOUBLE PRECISION DEFAULT 0,
  localizacao     TEXT DEFAULT '',
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE familia_atributos (
  id BIGSERIAL PRIMARY KEY,
  familia_id INTEGER NOT NULL ,
  nome TEXT NOT NULL,
  tipo TEXT NOT NULL DEFAULT 'lista',
  opcoes TEXT DEFAULT '[]',
  obrigatorio INTEGER NOT NULL DEFAULT 0,
  ordem INTEGER NOT NULL DEFAULT 0,
  validacao TEXT DEFAULT 'texto',
  UNIQUE(familia_id, nome)
);

CREATE TABLE familias (
  id BIGSERIAL PRIMARY KEY,
  nome TEXT NOT NULL UNIQUE,
  descricao TEXT DEFAULT '',
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  ncm_padrao TEXT DEFAULT '',
  unidade_padrao TEXT DEFAULT 'UN',
  sku_atributos JSONB
);

CREATE TABLE fiscal_config (
  id              BIGSERIAL PRIMARY KEY,
  variante_id     INTEGER NOT NULL ,
  ncm             TEXT DEFAULT '',
  cfop            TEXT,
  cst_icms        TEXT,
  cst_pis         TEXT,
  cst_cofins      TEXT,
  aliquota_icms   DOUBLE PRECISION DEFAULT 0,
  aliquota_pis    DOUBLE PRECISION DEFAULT 0,
  aliquota_cofins DOUBLE PRECISION DEFAULT 0,
  aliquota_ipi    DOUBLE PRECISION DEFAULT 0,
  origem INTEGER DEFAULT 0,
  cest TEXT DEFAULT '',
  csosn TEXT DEFAULT '',
  aliquota_icms_st DOUBLE PRECISION DEFAULT 0,
  mva DOUBLE PRECISION DEFAULT 0,
  base_reducao DOUBLE PRECISION DEFAULT 0,
  aliquota_interestadual DOUBLE PRECISION DEFAULT 0,
  aliquota_fecp DOUBLE PRECISION DEFAULT 0,
  credito_icms DOUBLE PRECISION DEFAULT 0,
  beneficio_id INTEGER ,
  vigencia_inicio TEXT,
  vigencia_fim TEXT,
  UNIQUE(variante_id)
);

CREATE TABLE fiscal_config_historico (
  id                      BIGSERIAL PRIMARY KEY,
  variante_id             INTEGER NOT NULL ,
  tipo                    TEXT NOT NULL DEFAULT 'atualizado'
                            CHECK(tipo IN ('criado','atualizado')),
  ncm                     TEXT DEFAULT '',
  cfop                    TEXT,
  cst_icms                TEXT,
  cst_pis                 TEXT,
  cst_cofins              TEXT,
  aliquota_icms           DOUBLE PRECISION DEFAULT 0,
  aliquota_pis            DOUBLE PRECISION DEFAULT 0,
  aliquota_cofins         DOUBLE PRECISION DEFAULT 0,
  aliquota_ipi            DOUBLE PRECISION DEFAULT 0,
  origem                  INTEGER DEFAULT 0,
  cest                    TEXT DEFAULT '',
  csosn                   TEXT DEFAULT '',
  aliquota_icms_st        DOUBLE PRECISION DEFAULT 0,
  mva                     DOUBLE PRECISION DEFAULT 0,
  base_reducao            DOUBLE PRECISION DEFAULT 0,
  aliquota_interestadual  DOUBLE PRECISION DEFAULT 0,
  aliquota_fecp           DOUBLE PRECISION DEFAULT 0,
  credito_icms            DOUBLE PRECISION DEFAULT 0,
  beneficio_id            INTEGER,
  vigencia_inicio         TEXT,
  vigencia_fim            TEXT,
  usuario_id              INTEGER ,
  criado_em               TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE fiscal_regra (
  id                 BIGSERIAL PRIMARY KEY,
  nome               TEXT NOT NULL,
  descricao          TEXT DEFAULT '',
  ativo              INTEGER NOT NULL DEFAULT 1,
  -- Critérios de correspondência ('' = qualquer)
    regime             TEXT DEFAULT '',
  uf_origem          TEXT DEFAULT '',
  uf_destino         TEXT DEFAULT '',
  tipo_cliente       TEXT DEFAULT '',
  contribuinte       TEXT DEFAULT '',
  finalidade         TEXT DEFAULT '',
  modelo_documento   TEXT DEFAULT '',
  natureza_operacao  TEXT DEFAULT '',
  ncm_prefixo        TEXT DEFAULT '',
  cest               TEXT DEFAULT '',
  origem             TEXT DEFAULT '',
  -- Resultado prescrito pela regra
    cfop               TEXT DEFAULT '',
  cst_icms           TEXT DEFAULT '',
  csosn              TEXT DEFAULT '',
  cst_pis            TEXT DEFAULT '',
  cst_cofins         TEXT DEFAULT '',
  cst_ibs            TEXT DEFAULT '',
  cst_cbs            TEXT DEFAULT '',
  modalidade_st      TEXT DEFAULT '',
  aliquota_icms      DOUBLE PRECISION,
  mva                DOUBLE PRECISION,
  base_reducao       DOUBLE PRECISION,
  aliquota_icms_st   DOUBLE PRECISION,
  aliquota_pis       DOUBLE PRECISION,
  aliquota_cofins    DOUBLE PRECISION,
  aliquota_ibs       DOUBLE PRECISION,
  aliquota_cbs       DOUBLE PRECISION,
  prioridade         INTEGER NOT NULL DEFAULT 100,
  observacao         TEXT DEFAULT '',
  criado_em          TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em      TEXT,
  dimensao TEXT NOT NULL DEFAULT 'geral'
);

CREATE TABLE fiscal_regra_auditoria (
  id              BIGSERIAL PRIMARY KEY,
  regra_id        INTEGER ,
  acao            TEXT NOT NULL
                    CHECK(acao IN ('criada','alterada','desativada','ativada','versao')),
  usuario_id      INTEGER ,
  valor_anterior  TEXT,
  valor_novo      TEXT,
  motivo          TEXT DEFAULT '',
  fonte           TEXT DEFAULT '',
  vigencia_inicio TEXT,
  vigencia_fim    TEXT,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE fiscal_regra_versao (
  id            BIGSERIAL PRIMARY KEY,
  regra_id      INTEGER NOT NULL ,
  versao        TEXT NOT NULL,
  fonte         TEXT DEFAULT '',
  data_inicio   TEXT NOT NULL,
  data_fim      TEXT,
  parametros    TEXT DEFAULT '{}',
  status        TEXT NOT NULL DEFAULT 'ativa'
                  CHECK(status IN ('ativa','inativa','rascunho')),
  criado_em     TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE fornecedor_preco (
  id              BIGSERIAL PRIMARY KEY,
  fornecedor_id   INTEGER NOT NULL ,
  variante_id     INTEGER NOT NULL ,
  preco           DOUBLE PRECISION NOT NULL,
  prazo_entrega   INTEGER,
  icms            DOUBLE PRECISION DEFAULT 0,
  ipi             DOUBLE PRECISION DEFAULT 0,
  moeda           TEXT DEFAULT 'BRL',
  data_validade   TEXT,
  ativo           INTEGER NOT NULL DEFAULT 1,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  UNIQUE(fornecedor_id, variante_id)
);

CREATE TABLE fornecedor_preferencial (
  id              BIGSERIAL PRIMARY KEY,
  variante_id     INTEGER NOT NULL ,
  fornecedor_id   INTEGER NOT NULL ,
  ranking         INTEGER NOT NULL DEFAULT 1,
  ultimo_preco    DOUBLE PRECISION,
  ultimo_prazo    INTEGER,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  UNIQUE(variante_id, fornecedor_id)
);

CREATE TABLE fornecedor_variantes (
  id BIGSERIAL PRIMARY KEY,
  variante_id INTEGER NOT NULL ,
  fornecedor_id INTEGER NOT NULL ,
  codigo_fornecedor TEXT DEFAULT '',
  descricao_fornecedor TEXT DEFAULT '',
  unidade_compra TEXT DEFAULT '',
  fator_conversao DOUBLE PRECISION NOT NULL DEFAULT 1,
  UNIQUE(variante_id, fornecedor_id)
);

CREATE TABLE fornecedores (
  id BIGSERIAL PRIMARY KEY,
  nome TEXT NOT NULL,
  razao_social TEXT DEFAULT '',
  cnpj_cpf TEXT DEFAULT '',
  representante TEXT DEFAULT '',
  whatsapp TEXT,
  email TEXT,
  observacoes TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE garantia (
  id                BIGSERIAL PRIMARY KEY,
  cliente_nome      TEXT NOT NULL DEFAULT '',
  cliente_id        INTEGER ,
  orcamento_id      INTEGER ,
  variante_id       INTEGER ,
  produto_nome      TEXT NOT NULL DEFAULT '',
  data_venda        TEXT,
  data_inicio       TEXT NOT NULL,
  data_fim          TEXT NOT NULL,
  dias              INTEGER NOT NULL DEFAULT 90,
  descricao         TEXT DEFAULT '',
  observacao        TEXT DEFAULT '',
  status            TEXT NOT NULL DEFAULT 'ativa'
                      CHECK(status IN ('ativa','vencida','acionada','cancelada')),
  criado_em         TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE ibpt (
  id              BIGSERIAL PRIMARY KEY,
  ncm             TEXT NOT NULL,
  descricao       TEXT DEFAULT '',
  aliquota_federal DOUBLE PRECISION DEFAULT 0,
  aliquota_estadual DOUBLE PRECISION DEFAULT 0,
  aliquota_municipal DOUBLE PRECISION DEFAULT 0,
  fonte           TEXT DEFAULT '',
  vigencia_inicio TEXT,
  vigencia_fim    TEXT,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE ibpt_sugestoes (
  id           BIGSERIAL PRIMARY KEY,
  variante_id  INTEGER NOT NULL ,
  ncm          TEXT NOT NULL,
  descricao    TEXT DEFAULT '',
  confianca    DOUBLE PRECISION NOT NULL DEFAULT 0,
  status       TEXT NOT NULL DEFAULT 'pendente'
                 CHECK(status IN ('pendente','aplicada','rejeitada')),
  criado_em    TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  aplicado_em  TEXT,
  UNIQUE(variante_id)
);

CREATE TABLE imagens_produto (
  id BIGSERIAL PRIMARY KEY,
  produto_id INTEGER NOT NULL ,
  variante_id INTEGER ,
  filename TEXT NOT NULL,
  ordem INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE impressao_config (
  id            INTEGER PRIMARY KEY CHECK (id = 1),
  driver        TEXT NOT NULL DEFAULT 'escpos_tcp',
  host          TEXT NOT NULL DEFAULT '127.0.0.1',
  porta         INTEGER NOT NULL DEFAULT 9100,
  papel_mm      INTEGER NOT NULL DEFAULT 80,
  auto_impressao INTEGER NOT NULL DEFAULT 0,
  ativo         INTEGER NOT NULL DEFAULT 1,
  atualizado_em TEXT
);

CREATE TABLE impressao_fila (
  id            BIGSERIAL PRIMARY KEY,
  tipo          TEXT NOT NULL DEFAULT 'orcamento',
  referencia    TEXT NOT NULL DEFAULT '',
  payload       TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pendente',
  erro          TEXT,
  criado_em     TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  processado_em TEXT
);

CREATE TABLE inventario_itens (
  id                  BIGSERIAL PRIMARY KEY,
  inventario_id       INTEGER NOT NULL ,
  variante_id         INTEGER NOT NULL ,
  deposito_id         INTEGER NOT NULL ,
  quantidade_sistema  DOUBLE PRECISION NOT NULL DEFAULT 0,
  quantidade_contada  DOUBLE PRECISION,
  divergencia         DOUBLE PRECISION,
  localizacao         TEXT DEFAULT '',
  criado_em           TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  UNIQUE(inventario_id, variante_id, deposito_id)
);

CREATE TABLE inventarios (
  id          BIGSERIAL PRIMARY KEY,
  nome        TEXT NOT NULL,
  deposito_id INTEGER ,
  data        TEXT NOT NULL DEFAULT (date('now')),
  status      TEXT NOT NULL DEFAULT 'aberto'
                CHECK(status IN ('aberto','finalizado')),
  criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE lotes (
  id              BIGSERIAL PRIMARY KEY,
  deposito_id     INTEGER NOT NULL ,
  variante_id     INTEGER NOT NULL ,
  codigo          TEXT NOT NULL,
  data_fabricacao TEXT,
  data_validade   TEXT,
  quantidade      DOUBLE PRECISION NOT NULL DEFAULT 0,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE movimento_bancario (
  id                BIGSERIAL PRIMARY KEY,
  conta_id          INTEGER NOT NULL ,
  tipo              TEXT NOT NULL CHECK(tipo IN ('credito','debito','transferencia')),
  valor             DOUBLE PRECISION NOT NULL,
  data_movimento    TEXT NOT NULL,
  data_conciliacao  TEXT,
  descricao         TEXT NOT NULL DEFAULT '',
  documento         TEXT DEFAULT '',
  categoria         TEXT DEFAULT '',
  plano_conta_id    INTEGER ,
  conciliado        INTEGER NOT NULL DEFAULT 0,
  criado_em         TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE nfe_entrada (
  id              BIGSERIAL PRIMARY KEY,
  chave           TEXT NOT NULL UNIQUE,
  numero          INTEGER NOT NULL,
  serie           INTEGER NOT NULL DEFAULT 1,
  fornecedor_nome TEXT NOT NULL,
  fornecedor_doc  TEXT DEFAULT '',
  valor           DOUBLE PRECISION NOT NULL,
  data_emissao    TEXT NOT NULL,
  xml             TEXT DEFAULT '',
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE nfe_saida (
  id              BIGSERIAL PRIMARY KEY,
  numero          INTEGER NOT NULL,
  serie           INTEGER NOT NULL DEFAULT 1,
  chave           TEXT DEFAULT '',
  status          TEXT NOT NULL DEFAULT 'digitada'
                    CHECK(status IN ('digitada','autorizada','cancelada','denegada')),
  orcamento_id    INTEGER ,
  cliente_nome    TEXT NOT NULL,
  cliente_doc     TEXT DEFAULT '',
  valor           DOUBLE PRECISION NOT NULL,
  xml             TEXT DEFAULT '',
  protocolo       TEXT DEFAULT '',
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE orcamento_itens (
  id               BIGSERIAL PRIMARY KEY,
  orcamento_id     INTEGER NOT NULL ,
  produto_id       INTEGER,
  nome             TEXT NOT NULL,
  sku              TEXT NOT NULL DEFAULT '',
  marca            TEXT NOT NULL DEFAULT '',
  especificacao    TEXT NOT NULL DEFAULT '',
  quantidade       DOUBLE PRECISION NOT NULL DEFAULT 1,
  preco_unitario   DOUBLE PRECISION NOT NULL DEFAULT 0,
  desconto_percentual DOUBLE PRECISION NOT NULL DEFAULT 0,
  subtotal         DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE TABLE orcamento_itens_fiscal (
  id                   BIGSERIAL PRIMARY KEY,
  orcamento_id         INTEGER NOT NULL ,
  item_id              INTEGER NOT NULL ,
  variante_id          INTEGER,
  data_operacao        TEXT,
  regime               TEXT,
  ncm                  TEXT,
  cest                 TEXT,
  cfop                 TEXT,
  origem               INTEGER,
  cst_icms             TEXT,
  csosn                TEXT,
  cst_pis              TEXT,
  cst_cofins           TEXT,
  cst_ibs              TEXT,
  cst_cbs              TEXT,
  aliquota_icms        DOUBLE PRECISION,
  base_icms            DOUBLE PRECISION,
  valor_icms           DOUBLE PRECISION,
  modalidade_st        TEXT,
  base_icms_st         DOUBLE PRECISION,
  aliquota_icms_st     DOUBLE PRECISION,
  valor_icms_st        DOUBLE PRECISION,
  aliquota_pis         DOUBLE PRECISION,
  valor_pis            DOUBLE PRECISION,
  aliquota_cofins      DOUBLE PRECISION,
  valor_cofins         DOUBLE PRECISION,
  aliquota_ibs         DOUBLE PRECISION,
  valor_ibs            DOUBLE PRECISION,
  aliquota_cbs         DOUBLE PRECISION,
  valor_cbs            DOUBLE PRECISION,
  regra_id             INTEGER,
  regra_nome           TEXT,
  regra_versao         TEXT,
  regra_fonte          TEXT,
  regra_origem         TEXT,
  regra_produto_id     INTEGER,
  regra_produto_nome   TEXT,
  regra_produto_versao TEXT,
  resultado_json       TEXT,
  status_validacao     TEXT,
  criado_em            TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE orcamentos (
  id           BIGSERIAL PRIMARY KEY,
  numero       TEXT NOT NULL UNIQUE,
  cliente      TEXT NOT NULL DEFAULT '',
  contato      TEXT NOT NULL DEFAULT '',
  validade_dias INTEGER NOT NULL DEFAULT 7,
  observacoes  TEXT NOT NULL DEFAULT '',
  status       TEXT NOT NULL DEFAULT 'rascunho',
  desconto     DOUBLE PRECISION NOT NULL DEFAULT 0,
  subtotal     DOUBLE PRECISION NOT NULL DEFAULT 0,
  total        DOUBLE PRECISION NOT NULL DEFAULT 0,
  criado_em    TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em TEXT,
  frete DOUBLE PRECISION DEFAULT 0,
  seguro DOUBLE PRECISION DEFAULT 0,
  despesas_acessorias DOUBLE PRECISION DEFAULT 0,
  base_icms DOUBLE PRECISION DEFAULT 0,
  valor_icms DOUBLE PRECISION DEFAULT 0,
  base_ipi DOUBLE PRECISION DEFAULT 0,
  valor_ipi DOUBLE PRECISION DEFAULT 0,
  base_pis_cofins DOUBLE PRECISION DEFAULT 0,
  valor_pis DOUBLE PRECISION DEFAULT 0,
  valor_cofins DOUBLE PRECISION DEFAULT 0,
  total_liquido DOUBLE PRECISION DEFAULT 0,
  condicao_pagamento_id INTEGER ,
  usuario_id INTEGER,
  desconto_autorizado INTEGER NOT NULL DEFAULT 0,
  desconto_autorizado_por INTEGER,
  desconto_autorizado_em TEXT,
  uf_destino TEXT,
  tipo_cliente TEXT,
  contribuinte TEXT,
  modelo_documento TEXT,
  cliente_id INTEGER,
  cliente_doc TEXT,
  ie TEXT
);

CREATE TABLE paginas_fonte (
  id BIGSERIAL PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  site TEXT DEFAULT '',
  html TEXT,
  bytes INTEGER DEFAULT 0,
  url_final TEXT DEFAULT '',
  produto_id INTEGER,
  variante_id INTEGER,
  origem TEXT DEFAULT '',
  criada_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizada_em TEXT
);

CREATE TABLE pedido_itens (
  id BIGSERIAL PRIMARY KEY,
  cotacao_id INTEGER NOT NULL ,
  cotacao_item_id INTEGER NOT NULL ,
  pedido_id INTEGER ,
  fornecedor_id INTEGER NOT NULL ,
  preco_unitario DOUBLE PRECISION NOT NULL,
  quantidade DOUBLE PRECISION NOT NULL,
  criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE pedidos_compra (
  id BIGSERIAL PRIMARY KEY,
  numero TEXT UNIQUE NOT NULL,
  cotacao_id INTEGER NOT NULL ,
  fornecedor_id INTEGER NOT NULL ,
  status TEXT NOT NULL DEFAULT 'enviado',
  observacoes TEXT,
  data_geracao TEXT,
  criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE plano_de_contas (
  id         BIGSERIAL PRIMARY KEY,
  codigo     TEXT NOT NULL,
  nome       TEXT NOT NULL,
  tipo       TEXT NOT NULL DEFAULT 'receita',
  pai_id     INTEGER ,
  ativo      INTEGER NOT NULL DEFAULT 1,
  criado_em  TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em TEXT
);

CREATE TABLE politica_descontos (
  id              BIGSERIAL PRIMARY KEY,
  nome            TEXT NOT NULL,
  tipo            TEXT NOT NULL DEFAULT 'percentual' CHECK(tipo IN ('percentual','valor_fixo')),
  valor_maximo    DOUBLE PRECISION NOT NULL DEFAULT 0,
  valor_minimo    DOUBLE PRECISION NOT NULL DEFAULT 0,
  perfil          TEXT DEFAULT '',
  ativo           INTEGER NOT NULL DEFAULT 1,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE politica_fretes (
  id              BIGSERIAL PRIMARY KEY,
  nome            TEXT NOT NULL,
  uf              TEXT NOT NULL DEFAULT '',
  valor_minimo_pedido DOUBLE PRECISION DEFAULT 0,
  valor_frete     DOUBLE PRECISION NOT NULL DEFAULT 0,
  tipo            TEXT NOT NULL DEFAULT 'fixo' CHECK(tipo IN ('fixo','percentual','por_kg')),
  ativo           INTEGER NOT NULL DEFAULT 1,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE precificacao_revisoes (
  id              BIGSERIAL PRIMARY KEY,
  tabela_id       INTEGER NOT NULL ,
  codigo          TEXT NOT NULL,
  descricao       TEXT DEFAULT '',
  data_cadastro   TEXT NOT NULL DEFAULT (date('now')),
  data_validade   TEXT,
  situacao        TEXT NOT NULL DEFAULT 'aberta' CHECK(situacao IN ('aberta','fechada')),
  cliente_id      INTEGER ,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE preco_historico (
  id              BIGSERIAL PRIMARY KEY,
  tabela_id       INTEGER NOT NULL ,
  variante_id     INTEGER NOT NULL ,
  preco_anterior  DOUBLE PRECISION NOT NULL DEFAULT 0,
  preco_novo      DOUBLE PRECISION NOT NULL,
  margem_pct      DOUBLE PRECISION,
  markup_pct      DOUBLE PRECISION,
  tipo            TEXT NOT NULL DEFAULT 'reajuste'
                    CHECK(tipo IN ('reajuste','manual','promocao')),
  origem          TEXT DEFAULT '',
  usuario_id      INTEGER ,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE produto_diagnostico_variacao (
  id              BIGSERIAL PRIMARY KEY,
  produto_id      INTEGER NOT NULL UNIQUE ,
  classificacao   TEXT NOT NULL CHECK(classificacao IN ('variacao_real','oferta_duplicada','cadastro_incompleto')),
  n_variantes     INTEGER NOT NULL DEFAULT 0,
  n_atributos     INTEGER NOT NULL DEFAULT 0,
  n_eans          INTEGER NOT NULL DEFAULT 0,
  observacao      TEXT NOT NULL DEFAULT '',
  revisado        INTEGER NOT NULL DEFAULT 0,
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em   TEXT
);

CREATE TABLE produtos_cadastro (
  id BIGSERIAL PRIMARY KEY,
  familia_id INTEGER ,
  nome TEXT NOT NULL,
  marca TEXT DEFAULT '',
  grupo_id INTEGER ,
  subgrupo_id INTEGER ,
  descricao TEXT DEFAULT '',
  categoria_id INTEGER ,
  subcategoria_id INTEGER ,
  termos_busca TEXT DEFAULT '',
  embalagem TEXT DEFAULT '',
  url TEXT DEFAULT '',
  external_id TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em TEXT,
  linha_produto TEXT DEFAULT '',
  classe_abc TEXT DEFAULT '',
  ordem_abc INTEGER DEFAULT 0,
  margem_lucro_estimada DOUBLE PRECISION,
  giro_esperado_mercado DOUBLE PRECISION,
  valor_agregado TEXT DEFAULT '',
  lucro_total_estimado DOUBLE PRECISION,
  em_linha INTEGER DEFAULT 1
);

CREATE TABLE promocao_itens (
  id                BIGSERIAL PRIMARY KEY,
  promocao_id       INTEGER NOT NULL ,
  variante_id       INTEGER NOT NULL ,
  preco_promocional DOUBLE PRECISION,
  UNIQUE(promocao_id, variante_id)
);

CREATE TABLE promocoes (
  id           BIGSERIAL PRIMARY KEY,
  nome         TEXT NOT NULL,
  tipo         TEXT NOT NULL CHECK(tipo IN ('percentual','valor_fixo')),
  valor        DOUBLE PRECISION NOT NULL,
  data_inicio  TEXT,
  data_fim     TEXT,
  ativo        INTEGER NOT NULL DEFAULT 1,
  criado_em    TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE scraper_sync (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  cotacao_remap_done INTEGER NOT NULL DEFAULT 0,
  atualizado_em TEXT
);

CREATE TABLE solicitacao_compra (
  id              BIGSERIAL PRIMARY KEY,
  codigo          TEXT NOT NULL,
  descricao       TEXT DEFAULT '',
  status          TEXT NOT NULL DEFAULT 'rascunho'
                    CHECK(status IN ('rascunho','pendente','aprovada','rejeitada','transformada')),
  data_solicitacao TEXT NOT NULL DEFAULT (date('now')),
  data_aprovacao  TEXT,
  usuario_id      INTEGER ,
  aprovador_id    INTEGER ,
  observacao      TEXT DEFAULT '',
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE solicitacao_itens (
  id              BIGSERIAL PRIMARY KEY,
  solicitacao_id  INTEGER NOT NULL ,
  variante_id     INTEGER NOT NULL ,
  quantidade      DOUBLE PRECISION NOT NULL,
  justificativa   TEXT DEFAULT '',
  criado_em       TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE subcategorias (
  id BIGSERIAL PRIMARY KEY,
  categoria_id INTEGER NOT NULL ,
  nome TEXT NOT NULL,
  codigo TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  UNIQUE(categoria_id, nome)
);

CREATE TABLE tabela_preco_itens (
  id           BIGSERIAL PRIMARY KEY,
  tabela_id    INTEGER NOT NULL ,
  variante_id  INTEGER NOT NULL ,
  preco        DOUBLE PRECISION NOT NULL,
  margem       DOUBLE PRECISION,
  ativo        INTEGER NOT NULL DEFAULT 1,
  UNIQUE(tabela_id, variante_id)
);

CREATE TABLE tabelas_preco (
  id           BIGSERIAL PRIMARY KEY,
  nome         TEXT NOT NULL,
  tipo         TEXT NOT NULL DEFAULT 'varejo'
                 CHECK(tipo IN ('varejo','atacado','contrato','promocional')),
  margem_padrao DOUBLE PRECISION DEFAULT 0,
  markup       DOUBLE PRECISION DEFAULT 0,
  ativo        INTEGER NOT NULL DEFAULT 1,
  criado_em    TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em TEXT
);

CREATE TABLE tecnospeed_config (
  chave         TEXT PRIMARY KEY,
  valor         TEXT NOT NULL DEFAULT '',
  atualizado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE tecnospeed_empresas (
  cpf_cnpj      TEXT PRIMARY KEY,
  certificado_id TEXT,
  empresa_cadastrada INTEGER NOT NULL DEFAULT 0,
  atualizado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE tolerancias_compra (
  id              BIGSERIAL PRIMARY KEY,
  fornecedor_id   INTEGER NOT NULL ,
  tolerancia_preco_pct DOUBLE PRECISION DEFAULT 10,
  tolerancia_qtd_pct   DOUBLE PRECISION DEFAULT 10,
  exige_aprovacao      INTEGER NOT NULL DEFAULT 1,
  UNIQUE(fornecedor_id)
);

CREATE TABLE unidades_compra (
  id            BIGSERIAL PRIMARY KEY,
  sigla         TEXT NOT NULL UNIQUE,
  descricao     TEXT NOT NULL DEFAULT '',
  ativo         INTEGER NOT NULL DEFAULT 1,
  criado_em     TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))
);

CREATE TABLE usuarios (
  id          BIGSERIAL PRIMARY KEY,
  nome        TEXT NOT NULL,
  login       TEXT NOT NULL UNIQUE,
  senha_hash  TEXT NOT NULL,
  perfil      TEXT NOT NULL DEFAULT 'vendedor',
  ativo       INTEGER NOT NULL DEFAULT 1,
  criado_em   TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em TEXT,
  desconto_limite_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
  autoriza_desconto INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE variante_atributos (
  id BIGSERIAL PRIMARY KEY,
  variante_id INTEGER NOT NULL ,
  atributo_id INTEGER NOT NULL ,
  valor TEXT NOT NULL,
  UNIQUE(variante_id, atributo_id)
);

CREATE TABLE variantes (
  id BIGSERIAL PRIMARY KEY,
  produto_id INTEGER NOT NULL ,
  sku TEXT DEFAULT '',
  ean TEXT DEFAULT '',
  preco DOUBLE PRECISION NOT NULL DEFAULT 0,
  preco_promocional DOUBLE PRECISION,
  old_price DOUBLE PRECISION,
  pix_price DOUBLE PRECISION,
  installment TEXT DEFAULT '',
  url TEXT DEFAULT '',
  external_id TEXT,
  marca TEXT DEFAULT '',
  observacao TEXT DEFAULT '',
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  custo_unitario DOUBLE PRECISION,
  preco_venda DOUBLE PRECISION,
  ncm TEXT DEFAULT '',
  peso DOUBLE PRECISION DEFAULT 0,
  dimensoes TEXT DEFAULT '',
  unidade_venda TEXT DEFAULT 'UN',
  embalagem DOUBLE PRECISION DEFAULT 1,
  fator_conversao DOUBLE PRECISION DEFAULT 1,
  localizacao TEXT DEFAULT '',
  unidade_tributavel TEXT DEFAULT '',
  atributos JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE vendedores (
  id            BIGSERIAL PRIMARY KEY,
  nome          TEXT NOT NULL,
  comissao_pct  DOUBLE PRECISION NOT NULL DEFAULT 0,
  ativo         INTEGER NOT NULL DEFAULT 1,
  criado_em     TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
  atualizado_em TEXT
);

CREATE INDEX idx_adiantamentos_tipo ON adiantamentos(tipo);

CREATE INDEX idx_caixa_data ON caixa_movimento(criado_em);

CREATE INDEX idx_caixa_tipo ON caixa_movimento(tipo);

CREATE INDEX idx_cest_ncm ON cest(ncm_prefix);

CREATE INDEX idx_cli_cont_cliente ON cliente_contatos(cliente_id);

CREATE INDEX idx_cli_end_cliente ON cliente_enderecos(cliente_id);

CREATE INDEX idx_clientes_doc ON clientes(doc);

CREATE INDEX idx_clientes_nome ON clientes(nome);

CREATE INDEX idx_clientes_vendedor ON clientes(vendedor_id);

CREATE INDEX idx_cotacao_itens_cotacao ON cotacao_itens(cotacao_id);

CREATE INDEX idx_cotacao_itens_produto ON cotacao_itens(produto_id);

CREATE INDEX idx_cotacao_precos_fornecedor ON cotacao_precos(fornecedor_id);

CREATE INDEX idx_cotacao_precos_status ON cotacao_precos(status);

CREATE INDEX idx_dev_orcamento ON devolucoes(orcamento_id);

CREATE INDEX idx_diag_classificacao ON produto_diagnostico_variacao(classificacao);

CREATE INDEX idx_diag_revisado ON produto_diagnostico_variacao(revisado);

CREATE INDEX idx_docfiscal_orc ON documentos_fiscais(orcamento_id);

CREATE INDEX idx_docfiscal_status ON documentos_fiscais(status);

CREATE INDEX idx_docfiscal_tecnospeed ON documentos_fiscais(tecnospeed_id);

CREATE INDEX idx_estoque_movimento_dep ON estoque_movimento(deposito_id);

CREATE INDEX idx_estoque_movimento_tipo ON estoque_movimento(tipo);

CREATE INDEX idx_estoque_movimento_var ON estoque_movimento(variante_id);

CREATE INDEX idx_estoque_saldo_dep_var ON estoque_saldo(deposito_id, variante_id);

CREATE INDEX idx_exp_dep ON expedicao(deposito_id);

CREATE INDEX idx_exp_status ON expedicao(status);

CREATE INDEX idx_familia_atributos_familia ON familia_atributos(familia_id);

CREATE INDEX idx_fisc_hist_data ON fiscal_config_historico(criado_em);

CREATE INDEX idx_fisc_hist_var ON fiscal_config_historico(variante_id);

CREATE INDEX idx_fiscal_audit_regra ON fiscal_regra_auditoria(regra_id);

CREATE INDEX idx_fiscal_regra_ativo ON fiscal_regra(ativo);

CREATE INDEX idx_fiscal_regra_regime ON fiscal_regra(regime);

CREATE INDEX idx_fiscal_var ON fiscal_config(variante_id);

CREATE INDEX idx_fiscal_versao_regra ON fiscal_regra_versao(regra_id);

CREATE INDEX idx_fp_forn ON fornecedor_preco(fornecedor_id);

CREATE INDEX idx_fp_var ON fornecedor_preco(variante_id);

CREATE INDEX idx_fpref_var ON fornecedor_preferencial(variante_id);

CREATE INDEX idx_garantia_cliente ON garantia(cliente_id);

CREATE INDEX idx_garantia_status ON garantia(status);

CREATE INDEX idx_ibpt_ncm ON ibpt(ncm);

CREATE UNIQUE INDEX idx_ibpt_ncm_uq ON ibpt(ncm);

CREATE INDEX idx_ibpt_sug_status ON ibpt_sugestoes(status);

CREATE INDEX idx_imagens_produto_produto ON imagens_produto(produto_id);

CREATE INDEX idx_impressao_fila_status ON impressao_fila(status);

CREATE INDEX idx_interacao_cliente ON cliente_interacao(cliente_id);

CREATE INDEX idx_interacao_data ON cliente_interacao(data_contato);

CREATE INDEX idx_inv_itens_inv ON inventario_itens(inventario_id);

CREATE INDEX idx_lotes_dep_var ON lotes(deposito_id, variante_id);

CREATE INDEX idx_mov_bancario_conc ON movimento_bancario(conciliado);

CREATE INDEX idx_mov_bancario_conta ON movimento_bancario(conta_id);

CREATE INDEX idx_mov_bancario_data ON movimento_bancario(data_movimento);

CREATE INDEX idx_nfe_saida_status ON nfe_saida(status);

CREATE INDEX idx_ofis_orcamento ON orcamento_itens_fiscal(orcamento_id);

CREATE INDEX idx_ofis_variante ON orcamento_itens_fiscal(variante_id);

CREATE INDEX idx_orcamento_itens_orcamento ON orcamento_itens(orcamento_id);

CREATE INDEX idx_pagar_fornecedor ON contas_pagar(fornecedor_id);

CREATE INDEX idx_pagar_status ON contas_pagar(status);

CREATE INDEX idx_pagar_venc ON contas_pagar(data_vencimento);

CREATE INDEX idx_paginas_fonte_produto ON paginas_fonte(produto_id);

CREATE INDEX idx_paginas_fonte_site ON paginas_fonte(site);

CREATE INDEX idx_paginas_fonte_variante ON paginas_fonte(variante_id);

CREATE INDEX idx_pi_promocao ON promocao_itens(promocao_id);

CREATE INDEX idx_plano_contas_pai ON plano_de_contas(pai_id);

CREATE INDEX idx_preco_hist_tabela ON preco_historico(tabela_id);

CREATE INDEX idx_preco_hist_variante ON preco_historico(variante_id);

CREATE INDEX idx_produtos_ativo ON produtos_cadastro(ativo);

CREATE INDEX idx_produtos_categoria_id ON produtos_cadastro(categoria_id);

CREATE INDEX idx_produtos_em_linha ON produtos_cadastro(em_linha);

CREATE INDEX idx_produtos_familia ON produtos_cadastro(familia_id);

CREATE INDEX idx_produtos_nome ON produtos_cadastro(nome );

CREATE INDEX idx_produtos_subcategoria_id ON produtos_cadastro(subcategoria_id);

CREATE INDEX idx_receber_cliente ON contas_receber(cliente_id);

CREATE INDEX idx_receber_status ON contas_receber(status);

CREATE INDEX idx_receber_venc ON contas_receber(data_vencimento);

CREATE INDEX idx_revisao_tabela ON precificacao_revisoes(tabela_id);

CREATE INDEX idx_sc_status ON solicitacao_compra(status);

CREATE INDEX idx_tpi_tabela ON tabela_preco_itens(tabela_id);

CREATE INDEX idx_tpi_variante ON tabela_preco_itens(variante_id);

CREATE INDEX idx_variante_atributos_atributo ON variante_atributos(atributo_id);

CREATE INDEX idx_variante_atributos_variante ON variante_atributos(variante_id);

CREATE INDEX idx_variantes_produto ON variantes(produto_id);

CREATE INDEX idx_variantes_produto_ativo ON variantes(produto_id, ativo);

-- Foreign keys (após todas as tabelas existirem)

ALTER TABLE caixa_movimento ADD CONSTRAINT fk_caixa_movimento_plano_conta_id FOREIGN KEY (plano_conta_id) REFERENCES plano_de_contas(id);
ALTER TABLE caixa_movimento ADD CONSTRAINT fk_caixa_movimento_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id);
ALTER TABLE caixa_movimento ADD CONSTRAINT fk_caixa_movimento_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE cliente_apoio_comercial ADD CONSTRAINT fk_cliente_apoio_comercial_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE;
ALTER TABLE cliente_apoio_comercial ADD CONSTRAINT fk_cliente_apoio_comercial_tabela_preco_id FOREIGN KEY (tabela_preco_id) REFERENCES tabelas_preco(id);
ALTER TABLE cliente_apoio_fiscal ADD CONSTRAINT fk_cliente_apoio_fiscal_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE;
ALTER TABLE cliente_contatos ADD CONSTRAINT fk_cliente_contatos_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE;
ALTER TABLE cliente_enderecos ADD CONSTRAINT fk_cliente_enderecos_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE;
ALTER TABLE cliente_interacao ADD CONSTRAINT fk_cliente_interacao_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE;
ALTER TABLE cliente_interacao ADD CONSTRAINT fk_cliente_interacao_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id);
ALTER TABLE cliente_interacao ADD CONSTRAINT fk_cliente_interacao_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE clientes ADD CONSTRAINT fk_clientes_vendedor_id FOREIGN KEY (vendedor_id) REFERENCES vendedores(id) ON DELETE SET NULL;
ALTER TABLE condicao_parcelas ADD CONSTRAINT fk_condicao_parcelas_condicao_id FOREIGN KEY (condicao_id) REFERENCES condicoes_pagamento(id) ON DELETE CASCADE;
ALTER TABLE contas_pagar ADD CONSTRAINT fk_contas_pagar_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id);
ALTER TABLE contas_pagar ADD CONSTRAINT fk_contas_pagar_plano_conta_id FOREIGN KEY (plano_conta_id) REFERENCES plano_de_contas(id);
ALTER TABLE contas_receber ADD CONSTRAINT fk_contas_receber_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id);
ALTER TABLE contas_receber ADD CONSTRAINT fk_contas_receber_plano_conta_id FOREIGN KEY (plano_conta_id) REFERENCES plano_de_contas(id);
ALTER TABLE cotacao_fornecedores ADD CONSTRAINT fk_cotacao_fornecedores_cotacao_id FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE;
ALTER TABLE cotacao_fornecedores ADD CONSTRAINT fk_cotacao_fornecedores_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id);
ALTER TABLE cotacao_itens ADD CONSTRAINT fk_cotacao_itens_cotacao_id FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE;
ALTER TABLE cotacao_precos ADD CONSTRAINT fk_cotacao_precos_cotacao_item_id FOREIGN KEY (cotacao_item_id) REFERENCES cotacao_itens(id) ON DELETE CASCADE;
ALTER TABLE cotacao_precos ADD CONSTRAINT fk_cotacao_precos_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id);
ALTER TABLE devolucoes ADD CONSTRAINT fk_devolucoes_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id);
ALTER TABLE devolucoes ADD CONSTRAINT fk_devolucoes_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE devolucoes ADD CONSTRAINT fk_devolucoes_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE documentos_fiscais ADD CONSTRAINT fk_documentos_fiscais_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE;
ALTER TABLE estoque_movimento ADD CONSTRAINT fk_estoque_movimento_deposito_id FOREIGN KEY (deposito_id) REFERENCES depositos(id);
ALTER TABLE estoque_movimento ADD CONSTRAINT fk_estoque_movimento_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE estoque_movimento ADD CONSTRAINT fk_estoque_movimento_lote_id FOREIGN KEY (lote_id) REFERENCES lotes(id);
ALTER TABLE estoque_movimento ADD CONSTRAINT fk_estoque_movimento_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE estoque_saldo ADD CONSTRAINT fk_estoque_saldo_deposito_id FOREIGN KEY (deposito_id) REFERENCES depositos(id);
ALTER TABLE estoque_saldo ADD CONSTRAINT fk_estoque_saldo_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE expedicao ADD CONSTRAINT fk_expedicao_deposito_id FOREIGN KEY (deposito_id) REFERENCES depositos(id);
ALTER TABLE expedicao_itens ADD CONSTRAINT fk_expedicao_itens_expedicao_id FOREIGN KEY (expedicao_id) REFERENCES expedicao(id) ON DELETE CASCADE;
ALTER TABLE expedicao_itens ADD CONSTRAINT fk_expedicao_itens_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id);
ALTER TABLE expedicao_itens ADD CONSTRAINT fk_expedicao_itens_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE familia_atributos ADD CONSTRAINT fk_familia_atributos_familia_id FOREIGN KEY (familia_id) REFERENCES familias(id) ON DELETE CASCADE;
ALTER TABLE fiscal_config ADD CONSTRAINT fk_fiscal_config_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id) ON DELETE CASCADE;
ALTER TABLE fiscal_config ADD CONSTRAINT fk_fiscal_config_beneficio_id FOREIGN KEY (beneficio_id) REFERENCES beneficios_fiscais(id);
ALTER TABLE fiscal_config_historico ADD CONSTRAINT fk_fiscal_config_historico_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE fiscal_config_historico ADD CONSTRAINT fk_fiscal_config_historico_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE fiscal_regra_auditoria ADD CONSTRAINT fk_fiscal_regra_auditoria_regra_id FOREIGN KEY (regra_id) REFERENCES fiscal_regra(id) ON DELETE SET NULL;
ALTER TABLE fiscal_regra_auditoria ADD CONSTRAINT fk_fiscal_regra_auditoria_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE fiscal_regra_versao ADD CONSTRAINT fk_fiscal_regra_versao_regra_id FOREIGN KEY (regra_id) REFERENCES fiscal_regra(id) ON DELETE CASCADE;
ALTER TABLE fornecedor_preco ADD CONSTRAINT fk_fornecedor_preco_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE CASCADE;
ALTER TABLE fornecedor_preco ADD CONSTRAINT fk_fornecedor_preco_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE fornecedor_preferencial ADD CONSTRAINT fk_fornecedor_preferencial_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE fornecedor_preferencial ADD CONSTRAINT fk_fornecedor_preferencial_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id);
ALTER TABLE fornecedor_variantes ADD CONSTRAINT fk_fornecedor_variantes_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id) ON DELETE CASCADE;
ALTER TABLE fornecedor_variantes ADD CONSTRAINT fk_fornecedor_variantes_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE CASCADE;
ALTER TABLE garantia ADD CONSTRAINT fk_garantia_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id);
ALTER TABLE garantia ADD CONSTRAINT fk_garantia_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id);
ALTER TABLE garantia ADD CONSTRAINT fk_garantia_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE ibpt_sugestoes ADD CONSTRAINT fk_ibpt_sugestoes_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id) ON DELETE CASCADE;
ALTER TABLE imagens_produto ADD CONSTRAINT fk_imagens_produto_produto_id FOREIGN KEY (produto_id) REFERENCES produtos_cadastro(id) ON DELETE CASCADE;
ALTER TABLE imagens_produto ADD CONSTRAINT fk_imagens_produto_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id) ON DELETE CASCADE;
ALTER TABLE inventario_itens ADD CONSTRAINT fk_inventario_itens_inventario_id FOREIGN KEY (inventario_id) REFERENCES inventarios(id) ON DELETE CASCADE;
ALTER TABLE inventario_itens ADD CONSTRAINT fk_inventario_itens_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE inventario_itens ADD CONSTRAINT fk_inventario_itens_deposito_id FOREIGN KEY (deposito_id) REFERENCES depositos(id);
ALTER TABLE inventarios ADD CONSTRAINT fk_inventarios_deposito_id FOREIGN KEY (deposito_id) REFERENCES depositos(id);
ALTER TABLE lotes ADD CONSTRAINT fk_lotes_deposito_id FOREIGN KEY (deposito_id) REFERENCES depositos(id);
ALTER TABLE lotes ADD CONSTRAINT fk_lotes_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE movimento_bancario ADD CONSTRAINT fk_movimento_bancario_conta_id FOREIGN KEY (conta_id) REFERENCES contas_bancarias(id) ON DELETE CASCADE;
ALTER TABLE movimento_bancario ADD CONSTRAINT fk_movimento_bancario_plano_conta_id FOREIGN KEY (plano_conta_id) REFERENCES plano_de_contas(id);
ALTER TABLE nfe_saida ADD CONSTRAINT fk_nfe_saida_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id);
ALTER TABLE orcamento_itens ADD CONSTRAINT fk_orcamento_itens_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE;
ALTER TABLE orcamento_itens_fiscal ADD CONSTRAINT fk_orcamento_itens_fiscal_orcamento_id FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE;
ALTER TABLE orcamento_itens_fiscal ADD CONSTRAINT fk_orcamento_itens_fiscal_item_id FOREIGN KEY (item_id) REFERENCES orcamento_itens(id) ON DELETE CASCADE;
ALTER TABLE orcamentos ADD CONSTRAINT fk_orcamentos_condicao_pagamento_id FOREIGN KEY (condicao_pagamento_id) REFERENCES condicoes_pagamento(id);
ALTER TABLE pedido_itens ADD CONSTRAINT fk_pedido_itens_cotacao_id FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE;
ALTER TABLE pedido_itens ADD CONSTRAINT fk_pedido_itens_cotacao_item_id FOREIGN KEY (cotacao_item_id) REFERENCES cotacao_itens(id);
ALTER TABLE pedido_itens ADD CONSTRAINT fk_pedido_itens_pedido_id FOREIGN KEY (pedido_id) REFERENCES pedidos_compra(id) ON DELETE SET NULL;
ALTER TABLE pedido_itens ADD CONSTRAINT fk_pedido_itens_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id);
ALTER TABLE pedidos_compra ADD CONSTRAINT fk_pedidos_compra_cotacao_id FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE;
ALTER TABLE pedidos_compra ADD CONSTRAINT fk_pedidos_compra_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id);
ALTER TABLE plano_de_contas ADD CONSTRAINT fk_plano_de_contas_pai_id FOREIGN KEY (pai_id) REFERENCES plano_de_contas(id) ON DELETE CASCADE;
ALTER TABLE precificacao_revisoes ADD CONSTRAINT fk_precificacao_revisoes_tabela_id FOREIGN KEY (tabela_id) REFERENCES tabelas_preco(id) ON DELETE CASCADE;
ALTER TABLE precificacao_revisoes ADD CONSTRAINT fk_precificacao_revisoes_cliente_id FOREIGN KEY (cliente_id) REFERENCES clientes(id);
ALTER TABLE preco_historico ADD CONSTRAINT fk_preco_historico_tabela_id FOREIGN KEY (tabela_id) REFERENCES tabelas_preco(id) ON DELETE CASCADE;
ALTER TABLE preco_historico ADD CONSTRAINT fk_preco_historico_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE preco_historico ADD CONSTRAINT fk_preco_historico_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE produto_diagnostico_variacao ADD CONSTRAINT fk_produto_diagnostico_variacao_produto_id FOREIGN KEY (produto_id) REFERENCES produtos_cadastro(id) ON DELETE CASCADE;
ALTER TABLE produtos_cadastro ADD CONSTRAINT fk_produtos_cadastro_familia_id FOREIGN KEY (familia_id) REFERENCES familias(id);
ALTER TABLE produtos_cadastro ADD CONSTRAINT fk_produtos_cadastro_categoria_id FOREIGN KEY (categoria_id) REFERENCES categorias(id);
ALTER TABLE produtos_cadastro ADD CONSTRAINT fk_produtos_cadastro_subcategoria_id FOREIGN KEY (subcategoria_id) REFERENCES subcategorias(id);
ALTER TABLE produtos_cadastro ADD CONSTRAINT fk_produtos_cadastro_grupo_id FOREIGN KEY (grupo_id) REFERENCES grupos(id);
ALTER TABLE produtos_cadastro ADD CONSTRAINT fk_produtos_cadastro_subgrupo_id FOREIGN KEY (subgrupo_id) REFERENCES subgrupos(id);
ALTER TABLE promocao_itens ADD CONSTRAINT fk_promocao_itens_promocao_id FOREIGN KEY (promocao_id) REFERENCES promocoes(id) ON DELETE CASCADE;
ALTER TABLE promocao_itens ADD CONSTRAINT fk_promocao_itens_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE solicitacao_compra ADD CONSTRAINT fk_solicitacao_compra_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE solicitacao_compra ADD CONSTRAINT fk_solicitacao_compra_aprovador_id FOREIGN KEY (aprovador_id) REFERENCES usuarios(id);
ALTER TABLE solicitacao_itens ADD CONSTRAINT fk_solicitacao_itens_solicitacao_id FOREIGN KEY (solicitacao_id) REFERENCES solicitacao_compra(id) ON DELETE CASCADE;
ALTER TABLE solicitacao_itens ADD CONSTRAINT fk_solicitacao_itens_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE subcategorias ADD CONSTRAINT fk_subcategorias_categoria_id FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE;
ALTER TABLE tabela_preco_itens ADD CONSTRAINT fk_tabela_preco_itens_tabela_id FOREIGN KEY (tabela_id) REFERENCES tabelas_preco(id) ON DELETE CASCADE;
ALTER TABLE tabela_preco_itens ADD CONSTRAINT fk_tabela_preco_itens_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id);
ALTER TABLE tolerancias_compra ADD CONSTRAINT fk_tolerancias_compra_fornecedor_id FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE CASCADE;
ALTER TABLE variante_atributos ADD CONSTRAINT fk_variante_atributos_variante_id FOREIGN KEY (variante_id) REFERENCES variantes(id) ON DELETE CASCADE;
ALTER TABLE variante_atributos ADD CONSTRAINT fk_variante_atributos_atributo_id FOREIGN KEY (atributo_id) REFERENCES familia_atributos(id) ON DELETE CASCADE;
ALTER TABLE variantes ADD CONSTRAINT fk_variantes_produto_id FOREIGN KEY (produto_id) REFERENCES produtos_cadastro(id) ON DELETE CASCADE;

-- FTS5 (produtos_fts) é criado em runtime no SQLite e não entra aqui;
-- no Postgres será substituído por tsvector/pg_trgm numa etapa futura.