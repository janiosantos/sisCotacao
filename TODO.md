# TODO — Análise e correção de possíveis bugs (para Codex)

> Este arquivo é um checklist para uma **análise de código focada em bugs**. Leia
> `AGENTS.md` e `CONTEXTO_SESSAO.md` antes de começar. Siga as convenções de
> teste (pytest, typecheck) e **NUNCA faça deploy** — apenas commit/push.

## Instruções gerais
- Contexto: ERP Casa LM (`ecommerce_scraper`), Flask + PostgreSQL 16 + React/Vite.
- Testes: `pytest` (env `TEST_PG_URL=postgresql+psycopg://catalog:catalog@localhost:5432/catalog_test`), 211 verdes hoje.
- Ao corrigir: rodar `py_compile`, os testes do módulo tocado e a suíte completa.
- Registrar o resultado ao final deste arquivo (seção "Resultado da análise").

---

## 1. Armazenamento de imagens — ALTA prioridade (área que já causou perda de dados)

Revisar a cadeia completa após as migrações 0093/0094/0096 (caminhos relativos, remoção de `url_origem`):

- [ ] `backend/catalog_server/services/imagens_service.py`
  - `_save_bytes` retorna **str relativo** (`cadastro/<id>/<nome>`) — confirmar que NENHUM chamador ainda trata como `Path` absoluto.
  - `salvar_uploads`/`baixar_de_url`/`_relpath`/`remover_arquivo` (resolve contra `IMAGES_DIR`) consistentes.
  - `_conteudo_duplicado` lê de `_folder(produto_id)` = `IMAGES_DIR/cadastro/<id>` — correto com caminhos relativos?
- [ ] `backend/catalog_server/services/imagens_lote.py` — `baixar_lote` usa o retorno relativo de `_save_bytes`; contadores `aplicadas`/`deduplicadas` corretos? favorita → capa?
- [ ] `backend/catalog_server/services/parse_url_service.py` e `backend/catalog_server/importar_catalogo.py` — INSERTs sem `url_origem`; nenhuma referência remanescente a `url_origem` em código (grep).
- [ ] `backend/catalog_server/repositories/produtos.py` — `add_imagem` sem `url_origem`; `delete_imagem`/`remover_arquivo` com caminho relativo.
- [ ] Migrações `0093/0094/0096`: idempotência (rodar 2x não corrompe), comportamento em banco vazio→head.
- [ ] **grep global**: `url_origem`, `_save_bytes(`, `str(target)` — nenhuma referência quebrada.

## 2. API pública `/api/publico/*` — ALTA prioridade

- [ ] `backend/catalog_server/blueprints/api_publico.py`
  - Ciclo de vida das conexões (`with system_conn()`) — houve bug de usar `conn` fora do bloco; conferir TODAS as funções.
  - Sanitização completa: nenhum campo interno (custo, NCM, fornecedores, classe_abc) vaza na listagem/detalhe.
  - Paginação: `has_more` correto; `limit` capado em 100.
  - Filtro `grupo` (código/nome, ILIKE) + `/api/publico/grupos` (produto inexistente → 404?).
  - CORS (headers) e preflight OPTIONS.
- [ ] `backend/catalog_server/repositories/catalog.py`
  - `list_products`/`_browse_flat`/`resumo_abc`: adição do parâmetro `grupo` não quebrou ordem de params/WHERE (SQL injection?); `_flat_card` campos `grupo`/`grupo_nome`.
  - Confirmar que outros chamadores de `list_products`/`resumo_abc` (blueprints internos) continuam corretos com a assinatura nova.

## 3. Imagens em lote (fornecedor) — revisar lógica

- [ ] `imagens_lote.py`: `buscar_fornecedor`, `preview_imagens` (dedup MD5, dimensões), `baixar_lote` (retry 1x, limites 20/20, dedup por produto, `deduplicadas`).
- [ ] Tratamento de erros de rede/timeout (requests) e HTML/JS-rendered dos sites (casadoeletricistasc vs casadosparafusos/anhanguera).

## 4. Infraestrutura TLS/nginx — revisar

- [ ] `frontend/nginx-entrypoint.sh`: seleção TLS/HTTP, wait do cert, loop de reload (`stat -c %Y`), traps/signals (shutdown limpo).
- [ ] `frontend/nginx.backend-routes.conf`: proxy com **variável** + `resolver 127.0.0.11` — confirmar que o comportamento do proxy não mudou (URI pass-through, headers). Possível efeito colateral conhecido de `proxy_pass` com variável.
- [ ] `frontend/nginx.conf` / `nginx.http.conf`: `default_server`, redirect 301, `/.well-known/acme-challenge/`.
- [ ] `deployment/compose/docker-compose.prod.yml`: comando do certbot (escape `$$`, wait do token), volumes, projeto `-p siscom`.
- [ ] `deployment/scripts/smoke.sh`: dual-scheme (https/http) — parse dos helpers `get`/`post`.

## 5. Frontend — revisar

- [ ] `frontend/src/api/client.ts`: `ImagemProduto` sem `url_origem`; `aplicarImagensLote` com `deduplicadas` opcional.
- [ ] `frontend/src/pages/produtos.tsx`: lista (sku+detalhe), `ModalImagensLote`, mensagens dedup.
- [ ] `frontend/public/demo-publico.html`: JS (sem framework) — busca, filtros (grupo/cat/subcat/marca), paginação, modal detalhe, escape HTML.

## 6. Melhorias/pendências que podem esconder bugs de dados

- [ ] **~4.275 produtos sem `grupo_id`** (fios desmembrados na unificação) — não aparecem no filtro por grupo.
- [ ] **~3.215 produtos sem imagem** — não há vínculo no filesystem; verificar se algum arquivo em `images/cadastro/<id>/` ficou órfão (sem linha) ou linha sem arquivo.
- [ ] `FERRAGENS`: não existe como grupo (há PAR=PARAFUSOS). Confirmar se é renomear ou criar.

---

## Resultado da análise (preencher)

| Área | Status | Bugs encontrados / correções |
|---|---|---|
| 1. Imagens | ☐ | |
| 2. API pública | ☐ | |
| 3. Imagens lote | ☐ | |
| 4. TLS/nginx | ☐ | |
| 5. Frontend | ☐ | |
| 6. Dados | ☐ | |

> Ao finalizar: atualize `CONTEXTO_SESSAO.md` (log + pendências) e faça commit/push.