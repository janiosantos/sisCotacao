# CONTEXTO_SESSAO — Estado do Projeto (leitura obrigatória para agentes)

> **Regra para agentes (opencode, Codex e afins):**
> 1. **LEIA este arquivo + `AGENTS.md` no início de cada sessão.**
> 2. **ATUALIZE ao final de cada sessão**: log de implementações, tarefas pendentes e próximos passos.
> 3. Nunca invente estado — reflita o que está realmente commitado/deployado.

---

## 1. O que é o projeto

ERP/Catálogo da **Casa LM** (materiais elétricos, parafusos, ferramentas). Nome técnico do repo: `ecommerce_scraper`
(raiz: `C:\Users\jpsantos\Documents\Projetos\ecommerce_scraper`; remoto `https://github.com/janiosantos/sisCotacao`, branch `main`).

- **Backend**: Python 3.14 · Flask · PostgreSQL 16 · `psycopg` (com shim `pgsql` que emula `sqlite3`)
- **Frontend**: React + TypeScript + Vite + Tailwind (SPA em `frontend/`)
- **Infra**: Docker Compose + nginx (proxy `/api`, `/images`, impressões e portal)
- **Site institucional** (em paralelo): `C:\Users\jpsantos\Documents\Projetos\CASA_LM\site` — consumirá a **API pública** deste backend.

## 2. Regras de ouro (não negociáveis)

1. **DEPLOY para STAGING/PRODUÇÃO SOMENTE com confirmação explícita do usuário.** Commit/push é seguro; deploy não.
2. Migrações **versionadas** em `backend/migrations/versions/` com `RISCO` + `MUDANCA` (o_que/porque). `AUTO_MIGRATE=0` — aplicar por comando explícito.
3. Todo código vai para Git (`main`). Frontend **nunca** acessa o PostgreSQL diretamente (só a API).
4. Mudança incompatível de contrato → Expand/Migrate/Contract (ciclo A–F).
5. Testar: backend `pytest` (207), frontend `npm run typecheck` + `npm run build` + vitest.
6. Fonte da verdade de imagens de produto = **filesystem** `images/cadastro/<produto_id>/`; banco guarda só o caminho relativo.

## 3. Ambientes e acesso

| Ambiente | Onde | Frontend | Observações |
|---|---|---|---|
| DEV (notebook) | Docker local | `http://localhost:8080` | código bind-mount; migrações por comando |
| VM | `jpsantos@10.189.14.9` (`~/Projetos/ecommerce_scraper`) | `http://10.189.14.9:8080` | sudo `Mudar@123`; sempre `git pull` antes de operar |
| STAGING | servidor (projeto `siscom-staging`) | `:8081` | banco nasce vazio e é migrado pelo pipeline |
| PRODUÇÃO | servidor | domínio | só recebe release confirmada |

- Banco dev: `localhost:5432/catalog` (catalog/catalog) — mesmo banco do docker local.
- Banco de teste: `catalog_test` (env `TEST_PG_URL=postgresql+psycopg://catalog:catalog@localhost:5432/catalog_test`).
- **Atenção**: rodar o backend FORA do docker grava imagens em `backend/images` (errado). Usar `IMAGES_DIR=C:\Users\jpsantos\Documents\Projetos\ecommerce_scraper\images`.

## 4. Estado atual

- **Versão publicada**: `v2.32.2` (produção e staging — produção antes do staging por exceção pedida).
- **Schema**: migrações `0052..0098` aplicadas no dev (schema_version 98). Cadeia: 92 → 93 → 94 → 96 → 97 (`cobranca_ambiente`) → 98 (`login_rate_limit`). A **0095 foi removida** (nunca commitada).
- **Hardening (Codex)**: RBAC deny-by-default (sem perfil → 403), `MAX_CONTENT_LENGTH`, `safe_http` (SSRF), rate limit de login (PostgreSQL, 5/300s), segredos de pagamento não vazam, `deploy.yml` passa `CATALOG_SECRET`/`POSTGRES_USER`/`POSTGRES_PASSWORD` (secrets do GitHub — obrigatório configurar). **215 testes** backend + 13 frontend verdes.
- **Imagens**: 189.094 linhas em `imagens_produto`, 0 sem arquivo físico; arquivos em `images/cadastro/`.
- **Produtos**: ~62.731 em `produtos_cadastro`; **~3.215 sem imagem** (fios desmembrados e afins).
- **API pública**: `GET /api/publico/produtos` (paginado: `offset`/`limit` máx 100 + `has_more`; busca `?q=`; filtros `categoria`, `subcategoria`, `marca`, `em_linha`), `GET /api/publico/produtos/{id}`, `GET /api/publico/categorias`, `GET /api/publico/marcas`. Sem token, CORS `*`, sem vazamento interno.
- **Página demo**: `GET /demo-publico.html` (busca, filtros, paginação, detalhe).
- **OpenAPI**: `backend/openapi.json` (60 paths) servido em `/api/openapi.json`.

## 5. Log de implementações (recentes)

| Versão | O que foi feito |
|---|---|
| **v2.32.2** | Paginação explícita em `/api/publico/produtos` (`has_more`), busca `?q=`; correção da página demo (erro claro de JSON); AGENTS.md com regra de deploy. Deploy prod→staging (exceção). |
| **v2.32.1** | Página demo `/demo-publico.html` (consome a API pública). |
| **v2.32.0** | API pública `/api/publico/*` (produtos/detalhe/categorias/marcas) + CORS + OpenAPI (56→60 paths). |
| **v2.31.0** | Imagens: `filename` relativo ao `IMAGES_DIR` (0093), padronização física em `cadastro/` (0094), **remoção da 0095** (nunca commitada), reconstrução de vínculos a partir do filesystem (0096, +81.305 linhas). 189.094 linhas, 0 quebradas. |
| **v2.30.0** | Imagens em lote por fornecedor (busca/preview/aplicar), dedup MD5, retry 1x, limites 20/20, favorita = capa. |
| **v2.29.x** | Busca: relevância por cobertura de palavras; spec distintivo no card (atributos+marca+unidade). |
| **v2.28.0** | Taxonomia grupos/subgrupos (0092), combobox categoria filtrado, `reclassificar_cabos`, `normalizar_subcategorias`. |
| **v2.27.0** | Descrição padronizada (nome+atributos+marca) + busca ILIKE/pg_trgm (0091; `produtos_fts` removido). |
| **v2.26.0** | Unificação produto/variante (0085–0090): variantes viraram produtos independentes; EAV `variante_atributos` dropado. |

## 6. Tarefas pendentes (priorizadas)

**Alta**
- [ ] **Ativar TLS/Let's Encrypt em produção** (`siscom.casalm.com.br`, DNS-01 via Cloudflare):
  criar `deployment/certbot/cloudflare.ini` (token Zone:DNS:Edit, chmod 600), ajustar o
  redirecionamento de porta para a 443 interna e `docker compose up -d --build` — ver
  `deployment/certbot/LEIA.md`. Renovação automática (certbot a cada 12h + nginx reload).
- [ ] Integrar o **site institucional** (`CASA_LM/site`) à API pública — apontar `siteConfig.ts` para `/api/publico/*` e consumir paginação (`has_more`).
- [ ] **Sincronizar a VM** (10.189.14.9) com os commits recentes: `git pull` + `docker compose up -d --build` + `versioning apply` (schema 96).

**Média**
- [ ] ~**3.215 produtos sem imagem** — aplicar "imagens em lote" por fornecedor (fios desmembrados, etc.).
- [ ] Homologação **Focus NFe** com credenciais reais (NF-e/NFC-e) — adapters prontos em staging.
- [ ] Ligar **`FISCAL_ENGINE_V2` em PRODUÇÃO** (após deploy autorizado das releases 1.11→2.14).
- [ ] Renomear pasta raiz para `casa-lm` (manual, fechar editores; o site já está em `CASA_LM/site`).

**Baixa / infra**
- [ ] Remover arquivos soltos `2.5mm²` sem linha em `images/cadastro/62455` e `62461` (restos de teste).
- [ ] Limpeza opcional: ~2.742 pastas `images/cadastro/<id>/` de produtos que não existem mais.
- [ ] Ampliar cobertura de testes frontend (vitest — esqueleto pronto).
- [ ] OpenAPI fase 2 (crescer por blueprint tocado).

## 7. Próximos passos sugeridos

1. Validar produção: `/api/health`, `/api/pronto`, `/api/publico/produtos?limit=5` (has_more), `/demo-publico.html`.
2. Sincronizar a VM.
3. Confirmar a integração do site institucional (buscar/filtrar/paginar pelo `has_more`).
4. Rodar "imagens em lote" para os produtos sem imagem (grupo ELE / fios).

## 8. Convenções de trabalho para agentes

- **Começar**: ler `AGENTS.md` + `CONTEXTO_SESSAO.md` + `DESENVOLVIMENTO.md` (histórico técnico) + `git log --oneline -15`.
- **Análise de bugs (Codex)**: usar o checklist `TODO.md` — registrar o resultado na seção final.
- **Terminar**: atualizar `CONTEXTO_SESSAO.md` (log + pendências + próximos passos) e commit/push.
- **Backend**: após alterar, `python -m py_compile <arquivo>`; testes `pytest` (env `TEST_PG_URL` apontando para `catalog_test`). 215 testes verdes hoje.
- **Frontend**: `npm run typecheck` e `npm run build` (a partir de `frontend/`); testes `npm test`.
- **Migração nova**: arquivo `NNNN_*.py` em `backend/migrations/versions/` com `VERSION`, `RISCO`, `NAME`, `MUDANCA`, `guard`, `forward`, `backward`. Aplicar no dev com `python -m catalog_server.versioning apply --origem local`. Testar banco vazio→head (o CI do staging faz isso).
- **Deploy**: NUNCA sem confirmação explícita do usuário (ver AGENTS.md). Apresentar resumo e aguardar.
- **Manter os dois ambientes em sincronia** (notebook ↔ VM) via git pull/push.

## 9. Registro da sessão atual

- **2026-08-29**: auditoria técnica/UX de todo o workspace concluída em modo somente leitura; nenhum deploy, restart, rebuild de ambiente ou migração foi disparado.
  - Backend: identificados riscos críticos de atomicidade no fechamento/reabertura de vendas, concorrência no saldo de estoque/caixa/contas, baixa automática de pagamentos, exposição de credenciais e SSRF/uploads sem limites.
  - Fiscal: emissão ainda deve ser tratada como não pronta para produção até XSD, assinatura, idempotência, autenticação de webhooks e homologação SEFAZ/Focus; há código estrutural com `aamm=0000` e campos tributários simplificados.
  - Frontend: build e typecheck passam, porém há módulos monolíticos, cliente HTTP sem cache/schema runtime, mistura React + DOM imperativo, modal sem ciclo completo de acessibilidade e cobertura funcional baixa.
  - Infra/testes: `python -m compileall` passou; `npm run typecheck`, `npm run build` e 13 testes Vitest passaram. Sem `TEST_PG_URL`, a suíte backend encerra por segurança; o `testpaths` do `pyproject.toml` evita a colisão com o subprojeto `cotacoes-ia-importer`.
  - Prioridade sugerida: (1) transação única/UoW com locks e idempotência para vendas/estoque/financeiro; (2) bloquear segredos/defaults e validar webhooks; (3) endurecer fetch/upload; (4) completar pipeline fiscal; (5) modularizar frontend e ampliar testes E2E.
- **2026-08-30**: pacote de hardening e consistência implementado localmente, sem deploy, restart ou migração aplicada em ambiente não-dev.
  - Vendas, reabertura, estoque, caixa, contas a receber e contabilidade passaram a compartilhar transação quando necessário, com `FOR UPDATE`, locks/advisory locks, validação de saldo e idempotência nas movimentações.
  - Segredos de provedores de pagamento não são mais expostos na API; credenciais vazias preservam o valor existente; ambiente de cobrança passou a ser persistido pela migração versionada `0097_cobranca_ambiente`.
  - RBAC deixou de aceitar bypass legado por token e usuários inativos são rejeitados; bootstrap administrativo não usa mais senha fixa em desenvolvimento e é bloqueado em produção sem configuração explícita.
  - Webhooks de pagamento/fiscal exigem segredo configurado, uploads têm limite global/extensões permitidas e downloads de imagens/HTML rejeitam SSRF, redirecionamentos inseguros e respostas acima do limite.
  - Modal principal recebeu foco inicial, trap de Tab, Escape, `aria-modal`/label e restauração de foco; contrato TypeScript de credenciais foi ajustado para segredos opcionais.
  - Validação: backend completo `215 passed`, pagamentos `7 passed`, frontend `13 passed`, `npm run typecheck`, `npm run build` e `py_compile` passaram. A configuração de produção agora exige `APP_VERSION`, credenciais PostgreSQL, `CATALOG_SECRET` e `CATALOG_ENV=production`.
  - Pendências intencionais: assinatura nativa por provedor nos webhooks, homologação real Focus/SEFAZ e validação fiscal XSD/assinatura, outbox/jobs assíncronos, rate limit distribuído e modularização ampla das telas React. Não ligar `FISCAL_ENGINE_V2` nem publicar sem confirmação explícita.
- **2026-08-30 (continuação)**: rate limit de login implementado com estado persistido no PostgreSQL e migração versionada `0098_login_rate_limit`; limita por IP e conta, retorna `429`/`Retry-After` e remove a janela após login válido. A suíte completa banco vazio → head terminou com `215 passed`.
  - A integração do site institucional não foi implementada porque o diretório `CASA_LM/site` não existe neste checkout; requer disponibilizar o projeto correto antes de alterar seus consumidores.
  - TLS/Let's Encrypt, sincronização da VM, homologação Focus/SEFAZ, ativação de `FISCAL_ENGINE_V2`, limpeza de imagens e renomeação da pasta continuam bloqueados por operação, credenciais, dados reais ou autorização de publicação.
  - Outbox/Celery permanece pendente: o projeto não possui worker/dependência configurado e a implementação exige definir quais integrações serão assíncronas e seu contrato de reprocessamento antes de alterar o fluxo fiscal/financeiro.
  - Plano sequencial das oito pendências registrado em `PLANO_EXECUCAO_8_PENDENCIAS.md`, com critérios de aceite, pré-requisitos e gates de rollback.
- **2026-08-30 (Fase 0 do plano)**: migrações `0097`+`0098` **aplicadas no DEV** (schema 98); suíte backend **215 passed** + typecheck/build frontend OK; `deploy.yml` corrigido para injetar `CATALOG_SECRET`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (secrets — sem isso o próximo deploy falharia). Regressões do hardening validadas ao vivo: Vendedor lê `/api/sistema/status` (200) e é negado em cadastrar produto (403); login com rate limit ok; API pública ok. Pendente de autorização: deploy de staging (P1), sincronizar VM (P7), integração do site `../CASA_LM/site` (P4).
- **2026-08-30 (P1 + P7 do plano)**: **Secrets configurados no GitHub** (`CATALOG_SECRET` aleatório, `POSTGRES_USER`/`POSTGRES_PASSWORD=catalog`). **Staging deploy validado** (run 33293628345, sucesso — migrações 0097/0098 em banco vazio→head, smoke, rate limit). **VM 10.189.14.9 sincronizada** (git pull até `4c77c8e`, stack rebuild, `versioning apply` → schema 98; health + pronto OK). Manifesto v2.34.0 (hardening) criado e pushado.
- **2026-08-30 (P8 dry-run)**: relatório de saneamento de imagens gerado e commitado (`reports/*`): 3.188 produtos sem imagem (3.181 ativos), 0 linhas quebradas, **5.648 arquivos órfãos (435 MB)** e **2.742 pastas órfãs (1.060 MB)**. Nenhum sem-imagem tem arquivo órfão (precisa lote por fornecedor). **Tarefa deixada pendente pelo usuário** (aguarda aprovação para lote + remoção).
- **2026-08-30 (P2 — Webhooks e segredos)**: **validação de assinatura/token nativo por provedor** implementada (`catalog_server/payments/`): Mercado Pago (x-signature HMAC-SHA256 + **anti-replay** por `ts` na janela `WEBHOOK_TS_WINDOW_MS`, default 5min), Asaas (`asaas-access-token`), EfiPay (`?token=` ou `x-efi-webhook-token`), Sicoob/TecnoSpeed (genérico `X-Webhook-Secret`; Sicoob usa mTLS na infra). Migração **0099** (`payment_provider_config.webhook_secret`), aplicada no dev (schema 99). `processar_webhook` valida **antes** de processar (401 em inválido); idempotência por `webhook_id` mantida (repetido não baixa 2x). Frontend: campo "Segredo do Webhook" na tela Integrações + tipo TS. **224 testes** backend verdes (8 novos de assinatura) + typecheck OK. **Não deployado** (aguarda autorização).
