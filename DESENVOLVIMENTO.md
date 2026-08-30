# DESENVOLVIMENTO — O que foi feito e como

> Histórico técnico do ERP Casa LM (`ecommerce_scraper`). Complementa o
> `AGENTS.md` (regras) e o `CONTEXTO_SESSAO.md` (estado/pendências). Descreve o
> **que** foi desenvolvido e **como** (abordagem técnica de cada frente).

---

## 1. Visão geral

ERP/Catálogo da Casa LM (materiais elétricos, parafusos e ferramentas).
Catálogo de ~62.731 produtos, vendas por orçamento→pedido, estoque, fiscal,
financeiro, compras e uma **API pública** para o site institucional.

- **Backend**: Python 3.14 · Flask · PostgreSQL 16 · `psycopg` com shim `pgsql`
  que emula a API do `sqlite3` (placeholders `?` → `%s`).
- **Frontend**: React + TypeScript + Vite + Tailwind (SPA).
- **Infra**: Docker Compose + nginx (proxy `/api`, `/images`, impressões, portal
  do fornecedor, e a API pública).

## 2. Arquitetura (camadas)

```
PostgreSQL → SQLAlchemy(sem ORM pesado) → Repositórios → Services → Blueprints/API (contrato) → Frontend
                                                                        └── API pública (/api/publico/*)
```

- **Repositórios** (`backend/catalog_server/repositories/`): SQL direto via
  `system_conn()` (shim `pgsql`). Ex.: `produtos.py`, `catalog.py`.
- **Services** (`backend/catalog_server/services/`): regras de negócio
  (imagens, busca, fiscal, contábil, impressão).
- **Blueprints** (`backend/catalog_server/blueprints/`): rotas HTTP.
- **Migrações** (`backend/migrations/versions/`): versionadas, aplicadas por
  comando (`python -m catalog_server.versioning apply`), `AUTO_MIGRATE=0`.
- **RBAC**: gate central em `app_factory._autorizar_acesso()` (perfis/recursos).

## 3. Frentes desenvolvidas e como

### 3.1 Unificação produto/variante (v2.26.0 — migrações 0085→0090)

**O que:** cada antiga `variantes` virou um produto independente em
`produtos_cadastro` (Opção A). Eliminou `variantes`, o EAV `variante_atributos`
e `variante_produto_map`.

**Como (Expand→Migrate→Contract):**
- **0085 (Expand):** colunas operacionais em `produtos_cadastro` (sku, ean,
  preco, custo, ncm, peso, dimensões, unidade_venda, embalagem…) + backfill da
  variante principal.
- **0086 (Migrate):** criou `variante_produto_map` + 3.048 produtos novos para
  variantes extras (total 62.731).
- **0087 (Reapontamento):** `variante_id` → `produto_id` em ~20 tabelas de
  negócio, **idempotente**, técnica de offset (preserva constraints únicas no
  espaço compartilhado de ids) e mescla `estoque_saldo` somando quantidades.
- **0088:** valores do EAV movidos para `produtos_cadastro.atributos` (JSONB
  por nome).
- **0089:** `reconciliar_estoque()` recriada com `produto_id`.
- **0090 (Contract):** `DROP` de `variantes`, `variante_atributos`,
  `variante_produto_map` (destrutiva; backup pré-aplicação).

**Resultado:** catálogo flat (1 produto = 1 card), sem editor de variações.

### 3.2 Busca e descrição padronizada (v2.27–v2.29)

- **0091:** `produtos_fts` removido; busca por **ILIKE + pg_trgm** em
  `repositories/busca.py`, com `descricao` padronizada = `nome + atributos +
  marca` (backfill em massa).
- **Relevância por cobertura de palavras** (v2.29): quanto mais palavras do
  termo casam, melhor o rank.
- **Spec distintivo no card** (`catalog._flat_card`): características que
  identificam a unidade (embalagem + atributos + marca + unidade), separadas da
  descrição completa.

### 3.3 Taxonomia grupos/subgrupos (v2.28.0 — 0092)

- **0092:** cria `grupos` (ELE, HID, FER, PAR, AUT, CON, SEG, CAS, MED, MOV) e
  `subgrupos`; `categorias.subgrupo_id`; vincula categorias e atribui os
  produtos ao grupo (58.456 produtos).
- Combobox de categoria **filtrado** por grupo/subgrupo no cadastro.
- Tarefas de manutenção: `reclassificar_cabos` (cabos elétricos → ELE) e
  `normalizar_subcategorias` (mescla duplicatas).

### 3.4 Imagens em lote por fornecedor (v2.30.0)

- `services/imagens_lote.py`: `buscar_fornecedor` (sites:
  casadoeletricistasc, casadosparafusos, anhangueraferramentas),
  `preview_imagens` (dedup por **MD5**, dimensões, size_kb),
  `baixar_lote` (retry 1x, limites 20 imagens/20 produtos, dedup **por produto**,
  **favorita → capa**, contador `deduplicadas`).
- `irmaos` (mesmo nome + marca + cor, variando bitola).
- Frontend: `ModalImagensLote` em `produtos.tsx`, lista com SKU + detalhe.

### 3.5 Armazenamento de imagens — relativo e sem url_origem (v2.31.0)

**O que:** `imagens_produto.filename` passou a guardar **caminho relativo ao
IMAGES_DIR** (`cadastro/<produto_id>/<nome>`); removida `url_origem`; nome de
arquivo limpo (`img_<md5(url)[:10]>.ext`), sem nome original.

**Como:**
- **0093:** converteu 107.789 caminhos absolutos → relativos (set-based, regex
  `(?:images[/\\])(.*)$` + normalização de `\`).
  > ⚠️ Uma 1ª execução desta migração (loop Python com `IMAGES_DIR` errado)
  > corrompeu ~86.935 filenames para "pelados" — foi a causa raiz de perda de
  > imagens no dev. **0096** reconstruiu os vínculos a partir do filesystem
  > (+81.305 linhas). A **0095** (limpeza destrutiva) foi **removida** da cadeia
  > (nunca commitada). Produção não foi afetada.
- **0094:** arquivos da convenção `images/<id>/` movidos para `images/cadastro/<id>/`.
- **0096:** reconstrói linhas a partir do filesystem (fonte da verdade);
  idempotente; em produção insere 0.
- Binários **sempre no filesystem** (nunca BLOB no banco) — melhor prática p/
  ERP (streaming, cache, backup).

### 3.6 API pública para o site institucional (v2.32–v2.33)

- `blueprints/api_publico.py`: rotas **sem token**, CORS `*`, somente leitura.
- Endpoints: `GET /api/publico/produtos` (paginado `offset`/`limit` máx 100 +
  `has_more`; busca `?q=`; filtros `categoria`, `subcategoria`, `marca`,
  `grupo`, `em_linha`), `GET /api/publico/produtos/{id}` (detalhe + todas as
  imagens), `GET /api/publico/categorias`, `GET /api/publico/marcas`,
  `GET /api/publico/grupos`.
- **Contrato sanitizado**: id, sku, ean, nome, marca, grupo/grupo_nome,
  categoria, subcategoria, preços, unidade, especificações, descrição,
  atributos, imagens. **Nunca** custo, NCM, fornecedores, classe ABC.
- Isenção na whitelist de auth (`/api/publico/` + GET/OPTIONS); fora do RBAC.
- Página demo `/demo-publico.html` (busca, filtros, paginação, modal de
  detalhe) servida pelo frontend (`frontend/public/`).
- OpenAPI: 60+ paths (tag `publico`).

### 3.7 TLS / Let's Encrypt em produção (v2.33.0/1)

**Cenário:** domínio `siscom.casalm.com.br` atrás de **CGNAT** (80/443 não
abertas) → desafio **DNS-01 via Cloudflare** (sem abrir porta).

- Imagem própria do certbot (`deployment/certbot/Dockerfile`) com
  `certbot-dns-cloudflare` (a oficial não inclui o plugin).
- `certbot` service: emite na 1ª subida, renova a cada 12h; aguarda o token em
  `/home/jpsantos/siscom/certbot/cloudflare.ini` (montado como **diretório**,
  fora do workspace do runner).
- `nginx-entrypoint.sh`: escolhe config TLS/HTTP conforme o certificado,
  recarrega quando o cert muda; `nginx.conf` (443 + redirect) e
  `nginx.http.conf` (fallback sem cert).
- `nginx.backend-routes.conf`: `resolver 127.0.0.11` + proxy com **variável** —
  o nginx **não crasha** no startup se `backend` não resolver (fim do
  `host not found in upstream`).
- `X-Forwarded-Proto/Host` ao backend → links de fornecedor viram `https://`.
- `smoke.sh`/`deploy.yml` tolerantes a TLS (https com `-k`, fallback http).

### 3.8 Hardening + Webhooks + Outbox (2026-08-30)

- **Hardening (Codex)**: RBAC deny-by-default, `MAX_CONTENT_LENGTH`, `safe_http`
  (SSRF em downloads/urls), login rate limit no PostgreSQL (0098), segredos de
  pagamento nunca retornados pela API. Manifesto v2.34.0.
- **P2 — Webhooks**: validação de assinatura/token **nativo por provedor**
  (MP x-signature HMAC-SHA256 + anti-replay por `ts`; Asaas `asaas-access-token`;
  EfiPay `?token=`; Sicoob/TecnoSpeed `X-Webhook-Secret`) — migração 0099
  (`webhook_secret`); **`webhook_log`** (0100) com logs/detalhe/rechecagem e tela
  Webhooks; `POST /api/webhooks/rechecagem` consulta os provedores das pendentes.
  Validado em staging (baixa por notificação Asaas sandbox pix/boleto).
- **P5 — Outbox**: Redis + worker RQ + scheduler (3 composes); rechecagem
  periódica + `rodar_outbox`; tabela **`outbox`** (0101) com retry/backoff
  exponencial (60s·2ⁿ), dead-letter (5 tentativas) e idempotência
  (`idempotencia_key`). **Webhook 503 enfileira a rechecagem da conta** — quando
  o provedor é configurado, o worker baixa sem nova notificação.

### 3.9 P6 — Frontend modularizado (2026-08-30)

- **29 telas → 93 módulos** em 26 pastas `src/pages/<tela>/` (extração verbatim,
  sem mudança de comportamento). Fases: (1) componentes top-level (compras,
  fiscal, pre-venda, precos, cotacoes, catalogo, posvenda, bancos, atualizacoes,
  historico, dashboard); (2) modal-forms autocontidos (clientes, fornecedores,
  usuarios, perfis); (3) modais CRUD (unidades, vendedores, plano_contas,
  solicitacoes, diagnostico_variacoes); mantidas sem extração viável: categorias,
  webhooks, recebimento.
- Contrato de erro `ApiError` (`status/code/details`) + `mensagemErro` no client.
- **Correção de encoding**: arquivos com acentos corrompidos por `Set-Content`
  ANSI (double-encoding UTF-8→cp1252→UTF-8) foram restaurados e um fixer
  cp1252 por bytes eliminou o mojibake em todo o frontend (dry-run = 0).
- **27 testes frontend** (era 13) + typecheck/build verdes.

## 4. Modelo de dados relevante

| Tabela | Papel |
|---|---|
| `produtos_cadastro` | Produto unificado (dados operacionais + `atributos` JSONB + `grupo_id`) |
| `imagens_produto` | `produto_id`, `filename` (relativo), `ordem` (0 = capa) |
| `grupos` / `subgrupos` / `categorias` | Taxonomia (código/nome) |
| `variantes` / `variante_atributos` / `variante_produto_map` | **Dropadas** (0090) |
| `schema_migrations` | Controle de versões (52..101) |

## 5. Como rodar e testar

- **Dev (docker):** `docker compose up -d`; frontend `http://localhost:8080`;
  migrações: `docker compose exec -T backend python -m catalog_server.versioning apply --origem local`.
- **Backend tests:** `$env:TEST_PG_URL="postgresql+psycopg://catalog:catalog@localhost:5432/catalog_test"; python -m pytest` (234 verdes).
- **Frontend:** `npm run typecheck` e `npm run build` (em `frontend/`).
- **Compilar:** `python -m py_compile <arquivo>`.
- **IMPORTANTE:** rodar o backend fora do docker grava imagens em
  `backend/images` (errado). Usar `IMAGES_DIR=C:\...\ecommerce_scraper\images`.

## 6. Convenções de desenvolvimento

- Migrações versionadas com `RISCO`/`MUDANCA`; **idempotentes**; destrutivas só
  com backup.
- **Deploy só com confirmação explícita** do usuário (nunca automático).
- Frontend nunca acessa o banco — só a API.
- Expansão de contrato em etapas (Expand/Migrate/Contract) para mudanças
  incompatíveis.
- Docs de coordenação: `AGENTS.md` (regras) + `CONTEXTO_SESSAO.md` (estado).
- Análise de bugs para o Codex: `TODO.md`.

## 7. Referências (arquivos-chave)

| Assunto | Arquivo |
|---|---|
| API pública | `backend/catalog_server/blueprints/api_publico.py` |
| Catálogo | `backend/catalog_server/repositories/catalog.py` |
| Imagens (service) | `backend/catalog_server/services/imagens_service.py` |
| Imagens em lote | `backend/catalog_server/services/imagens_lote.py` |
| Produtos (repo) | `backend/catalog_server/repositories/produtos.py` |
| Migrações | `backend/migrations/versions/0085..0101` |
| Página demo | `frontend/public/demo-publico.html` |
| nginx TLS/HTTP | `frontend/nginx.conf` · `frontend/nginx.http.conf` · `frontend/nginx-entrypoint.sh` |
| Compose produção | `deployment/compose/docker-compose.prod.yml` |
| Certbot | `deployment/certbot/Dockerfile` · `LEIA.md` · `cloudflare.ini.example` |