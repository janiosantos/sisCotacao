# AGENTS.md

## ⛔ REGRA OBRIGATÓRIA: deploy só com confirmação explícita

**NUNCA disparar deploy para STAGING ou PRODUÇÃO (nem rebuild/restart de containers, nem
aplicação de migrações em ambientes não-dev) sem confirmação explícita do usuário.**

- Após implementar/corrigir, apresentar o resumo e **AGUARDAR o usuário pedir a publicação**.
- O usuário decide quando publicar — deploys automáticos travam o ciclo de desenvolvimento
  (correções e novas implementações acontecem o tempo todo).
- Manter as mudanças commitadas/pushadas (o que é seguro), mas **não** acionar workflows de
  deploy por conta própria.
- Exceção: nenhuma. Se houver urgência declarada, perguntar antes.

## 📋 CONTEXTO_SESSAO.md — leitura e atualização obrigatórias

Este projeto é trabalhado por **múltiplos agentes de codificação** (opencode, Codex e afins).
- **LEIA `CONTEXTO_SESSAO.md` no início de toda sessão** (estado do projeto, logs, pendências, próximos passos).
- **ATUALIZE ao final de toda sessão**: log do que foi implementado, tarefas pendentes e próximos passos.
- Mantenha sempre fiel ao estado real (commitado/deployado).

## Aplicação de patches

Os patches (arquivos `.patch`, normalmente em `PATCH/`) são aplicados **em ordem sequencial**.

- O patch N+1 pode corrigir ou implementar algo introduzido pelo patch N.
- Ao aplicar um patch, **o conteúdo do patch tem prioridade sobre o código já existente**. Em caso de conflito, o patch vence, mesmo que isso reverta ou sobrescreva mudanças de um patch anterior.
- O patch é aplicado **de forma integral, nunca seletiva**: todos os arquivos e todas as mudanças do patch entram. Não usar `--exclude`, não pular hunks nem aplicar só o que "falta". O estado final de cada arquivo tocado pelo patch deve ser exatamente o que o patch produz.
- Técnica recomendada para patches cumulativos (gerados sobre uma base comum, ex.: `ab4fb52`): aplicar o patch completo num worktree limpo na base e sincronizar o resultado integral para o working tree, em vez de aplicar parcialmente.

## Verificação

Depois de aplicar um patch:
- Python: `py_compile` nos arquivos alterados.
- Frontend: `npm run typecheck` (a partir de `frontend/`).

---

# Checklist de alterações que impactam produção

> **Obrigatório observar em toda proposta de alteração/correção** que toque no que já está funcionando.
> Estratégia-base: migrações versionadas + compatibilidade retroativa + **Expand/Migrate/Contract** + pipeline de publicação autorizada + versionamento dos contratos entre camadas.

## 1. As 12 Regras (status atual)

| # | Regra | Status |
|---|---|---|
| 01 | Todo schema change → migração versionada (`backend/migrations/versions/`, com `RISCO` + `MUDANCA`) | ✅ vigente |
| 02 | Todo código → Git | ✅ |
| 03 | Todo container → versão/tag (`backend:vX.Y.Z`, não só `latest`) | ✅ |
| 04 | Todo endpoint importante → contrato documentado (OpenAPI fase 1 em `/api/openapi.json`; cresce por blueprint tocado) | 🟡 fase 1 ✅ |
| 05 | Mudança incompatível → Expand/Contract (ciclo A–F) | ✅ regra vigente |
| 06 | Migration → testada automaticamente (banco vazio→head no gate de staging/CI) | ✅ |
| 07 | Produção → nunca alteração manual de schema | ✅ (`AUTO_MIGRATE=0` + advisory lock) |
| 08 | Frontend → nunca acesso direto ao PostgreSQL | ✅ |
| 09 | Migration destrutiva → somente após período de compatibilidade | ✅ (etapa F) |
| 10 | Toda release → plano de rollback nas duas dimensões (app × banco) | ✅ |
| 11 | Produção → backup antes de migration relevante | ✅ (pipeline) |
| 12 | Deploy → health check + smoke test | ✅ |

## 2. Visão obrigatória: 4 componentes + contratos

RELEASE coordena: **Schema PostgreSQL · Backend API · Frontend UI · Docker Images** — e o quinto elemento: os **CONTRATOS** entre eles (o que cada camada pode esperar da outra). Exemplo: frontend espera `GET /api/products → {id, name, sku}`; remover `sku` exige transição, nunca remoção direta.

Arquitetura-alvo em camadas: `PostgreSQL → SQLAlchemy → Service → API/Schema (contrato) → Frontend`. Nunca o frontend acoplado a modelos internos.

## 3. Estratégia: Expand → Migrate → Contract

Ciclo completo em releases separadas (exemplo de referência: mover `product.sku` para `product_variant.sku`):

| Etapa | Regra central |
|---|---|
| **A – Expand** | Criar a estrutura nova sem remover nada; antigo+novo coexistem; app segue funcionando |
| **B – Backfill** | Copiar dados antigo→novo; **idempotente** (2× não duplica nem corrompe); base grande ⇒ **em lotes** |
| **C – Dual Write** | Backend escreve nos dois lados, com validação de sincronia |
| **D – Trocar leitura** | Ler somente o novo mantendo o **contrato da API intacto** (o frontend nem percebe o banco mudar) |
| **E – Frontend** | Só agora mudar o contrato visível (`product` + `variants[]`), em etapa própria |
| **F – Contract** | `DROP` apenas quando frontend+backend+jobs+relatórios+integrações confirmadamente não usarem mais o antigo |

Consumidores a mapear antes de qualquer DROP/RENAME/troca de tipo: blueprints, repositórios, templates Jinja (`produtos_fts`, etiquetas…), relatórios, scripts, jobs (impressão, IA), integrações (portal do fornecedor, SEFAZ/Focus, TecnoSpeed).

## 4. Regras complementares

- **Regra de ouro**: jamais Banco novo ↓ Backend novo ↓ Frontend novo numa única tacada (ponto único de falha). Sequência R1 (expand) → R2 (adotar) → R3 (troca completa) → R4 (remover legado); cada etapa intermediária deixa o sistema **100% funcional** para quem ainda não foi atualizado.
- **Frontend nunca conhece o banco**: muda a tabela, a resposta da API continua igual até decisão consciente de mudar contrato.
- **Feature flags** em mudanças grandes: rollback comportamental independente do estrutural (flag `false` ≠ desfazer migration).
- **Rollback em duas dimensões**: aplicação (imagens `prev`) × banco (dump pré-migração). Destrutiva sempre por último; plano documentado por migração destrutiva.
- **Compatibilidade entre versões**: backend antigo ↔ PG ↔ backend novo devem funcionar durante toda a transição (protege também o rollback via `prev`).
- **Blue/Green/canary**: evolução futura se o sistema crescer — mesmo princípio em escala.

## 5. Ambientes

DEV (diário) → **STAGING** (✅ existe: projeto `siscom-staging` no servidor, frontend `:8081`, banco próprio que nasce vazio e é migrado pelo workflow **Deploy Staging**; valida qualquer branch antes da produção) → PRODUÇÃO (só recebe release aprovada).

### Ambientes DEV duais (v2.25.0)
O ambiente de desenvolvimento roda **em dois hosts em paralelo** (o serviço não para ao alternar o notebook):
- **Notebook (local)**: stack Docker no workspace, frontend `http://localhost:8080`.
- **VM 10.189.14.9** (Ubuntu `dsktop`): stack Docker em `~/Projetos/ecommerce_scraper`, frontend `http://10.189.14.9:8080`. Acesso SSH: `jpsantos@10.189.14.9` (chave pública do notebook; sudo com senha `Mudar@123`).

**Sincronização**: código via git (push/pull no GitHub — main commitada). Dados/banco e `images/` (uploads de produtos) migrados do notebook para a VM uma vez (v2.25.0). O `docker-compose.yml` monta `./images:/app/images`.

**Acesso ao código na VM**: VS Code **Remote-SSH** → `jpsantos@10.189.14.9` → `~/Projetos/ecommerce_scraper` (HMR funciona).
**Ferramentas na VM**: Docker 29 + Compose 2.40, Git 2.53, Python 3.14, **opencode** (v1.18.23 em `~/.opencode/bin`, PATH no `~/.bashrc`). Instalar extras: `ssh ... "echo 'Mudar@123' | sudo -S apt-get install -y <pkg>"`.

> ⚠️ Ao alterar algo na VM, lembrar que o código é o mesmo do notebook via git — sempre `git pull` na VM antes de operar, e `git push` após alterações para manter os dois em sincronia. Migrações são idempotentes (rodam em ambos).

## 6. Pipeline, Release Manifest e fluxo completo

Ordem de produção: **Backup → Migration Job (nunca dentro do `compose up`) → Health Check → Backend rollout → Frontend rollout → Smoke Tests**.

Imagens Docker empacotam release imutável e são **taggeadas com a versão** (`siscom-backend:vX.Y.Z`). O PostgreSQL é serviço persistente — atualizar containers nunca o recria.

**Release Manifest** (`releases/vX.Y.Z.json`) — notas + mapa técnico:

```json
{
  "versao": "v1.8.0",
  "componentes": ["backend", "schema"],
  "correcoes": ["..."], "melhorias": ["..."], "recursos": ["..."],
  "imagens": { "backend": "siscom-backend:v1.8.0", "frontend": "siscom-frontend:v1.8.0" },
  "database": { "migration": 47 },
  "api": { "versao": "v1" },
  "requires": { "postgres": ">=16" },
  "features": { "product_variants": true }
}
```

Fluxo ponta a ponta:
```
DESENVOLVIMENTO: migration → tabelas → modelos → API compatível → testes BE → testes FE
CI → STAGING: executar migration → testes E2E
PRODUÇÃO (autorizada): migration → backend → frontend → monitoramento
SÓ DEPOIS: remover estrutura antiga (Contract)
```

## 7. Checklist operacional (43 itens)

**Classificação**
1. [ ] Componentes afetados identificados? (schema/backend/frontend/imagens → manifesto)
2. [ ] Algum contrato rompe? (DB↔Backend, Backend↔Frontend, Frontend↔Backend)
3. [ ] Se rompe: etapas A–F definidas?
4. [ ] Coexistência de versões garantida durante a transição?
5. [ ] A proposta evita alterar tudo ao mesmo tempo? (regra de ouro)

**Banco**
6. [ ] Consumidores do campo mapeados? (código/templates/FTS/jobs/integrações)
7. [ ] Backfill idempotente? Base grande ⇒ em lotes?
8. [ ] Dual write com validação de sincronia antes de trocar leitura?
9. [ ] Destrutiva somente na etapa F, após confirmação classe por classe?
10. [ ] Migração testada nos dois caminhos: fresca (vazio→head) e incremental (N→head)?
11. [ ] Teste cobre o conjunto Migration+Banco+Backend?
12. [ ] Backup antes de migration relevante?

**API/Frontend**
13. [ ] Contrato da API atualizado na mesma release?
14. [ ] Troca interna invisível ao frontend (camada de serviço preservada)?
15. [ ] Frontend não conhece tabelas/colunas — só a API?
16. [ ] Feature flag para retorno comportamental independente?

**Publicação**
17. [ ] Manifesto com escopo correto + mapa técnico (imagens↔migration↔API↔requisitos↔features)?
18. [ ] Imagens taggeadas com a versão?
19. [ ] Validada em STAGING antes de produção?
20. [ ] Smoke tests pós-deploy executados?
21. [ ] Plano de rollback nas duas dimensões documentado?

*(Itens 22–24 do rascunho original foram incorporados aqui como 13–21; numeração consolidada.)*

## 8. Dívidas técnicas declaradas (ordem sugerida)

1. Tag de imagem por release (pequeno — workflow)
2. ~~Smoke tests no pipeline~~ ✅ **quitada na v1.7.0**
3. ~~CI com testes automatizados~~ ✅ **quitada na v1.8.0** (gate no staging + workflow manual)
4. ~~STAGING~~ ✅ **quitada na v1.6.5** (projeto `siscom-staging` + workflow *Deploy Staging*)
5. ~~OpenAPI~~ 🟡 **fase 1 entregue na v1.10.0** (fase 2: cobertura por blueprint tocado)
6. ~~Infraestrutura de feature flags~~ ✅ **quitada na v1.9.0** (sistema_flags + painel)

> Até as dívidas restantes fecharem, substituto mínimo aceitável: E2E local com Postgres descartável + validação live pós-deploy dos endpoints afetados (prática das releases v1.6.x). Para mudanças relevantes, o padrão atual é: validar a branch via **Deploy Staging** antes de autorizar produção.

## 9. Regras de domínio — onde consultar

### 9.1 Módulo Tributário / Fiscal

**Obrigatório consultar antes e durante qualquer trabalho no domínio fiscal.**

| Consultar | Onde |
|---|---|
| Diretrizes gerais do ERP + 10 regras permanentes | `MODULO_TRIBUTARIO.md` |
| Manifesto do kit | `INSTRUCOES_MODULO_TRIBUTARIO.md` |
| Regras por domínio (fiscal · banco · api · arquitetura · segurança) | `.agents/rules/<domínio>.md` |
| Skills profundas (**fiscal-mg** · fiscal-engine · database · api-backend · frontend · testing · deployment) | `.agents/skills/<domínio>/SKILL.md` |
| Workflows (nova feature · **regra fiscal** · migration · release) | `.agents/workflows/<fluxo>.md` |
| Documentação fiscal (ADRs · matriz de cenários baseline · fontes oficiais · modelo de dados) | `docs/fiscal/` |

**Princípio central do domínio:** `NCM → imposto` é proibido. Resultado = Produto + Contexto + Legislação vigente → **Motor Fiscal** → resultado versionado, explicável e auditável. Em dúvida: `FISCAL_REVIEW_REQUIRED`.

> 🔜 Estrutura equivalente para os módulos **Produtos** e **Estoque** entra nesta seção quando recebida (9.2).


### 9.2 Módulo Produtos e Estoque

| Consultar | Onde |
|---|---|
| Diretrizes do agente fiscal-comercial (missão, princípios #1-7, modelo mental Produto→Variação→TaxRule→InvoiceItem) | \AGENT-produtos.md\ |
| Regras por domínio (products · inventory · kardex · accounting · fiscal · api · security · EAN/GTIN) | \.agents/rules/*-produtos.md\ |
| Skills profundas (product-catalog · inventory · kardex · accounting · fiscal-engine/matrix/emission · fastapi-integration · testing) | \.agents/skills/<domínio>/SKILL-produtos.md\ |
| Workflows (product-lifecycle · stock-movement · order-to-cash · fiscal-document/rule · nfce-contingency · accounting-posting · migration · release) | \.agents/workflows/*-produtos.md\ |
| Modelo de dados/schema de negócio, regras ACID faturamento, NFC-e offline, Focus NFe | \docs/erp/\ |

**Princípios centrais:** estoque movimentado por fatos auditáveis com saldo derivado/reconciliável; atributos flexíveis em JSONB sem substituir colunas estruturais; CST/CFOP/CSOSN são SAÍDA de regra contextual, nunca verdades fixas da variação; convenção de incerteza CONFIRMADO/INFERIDO/A CONFIRMAR/BLOQUEADO.

## 10. Compromissos pendentes (próximas sessões)

### Cadastro de Produtos — melhorias de COMPLETUDE dentro das abas (estilo atual: abas, não página única)
1. **Indicador de completude** em Dados Gerais (obrigatórios preenchidos × pendentes). ✅ **entregue (v2.15.0)** — card lateral com progresso e pendências.
2. **Estoque por depósito + situação** (ok/ruptura/excesso) na tabela da aba Variações. ✅ **entregue (v2.15.0)** — filtro `produto_id` em `/api/estoque/saldo` + tabela por depósito com badges na aba Variações.
3. **Perfil Fiscal**: mostrar herdado do produto vs override por variação (hierarquia v2.5.0) + validação inline (marca, formato NCM, preço>0). ✅ **entregue (v2.15.0)** — `GET /api/fiscal/perfil-efetivo/{variante_id}` + painel com badges herdado/override e validações inline.

### Estoque / Contábil
4. **v2.15.0**: gatilhos contábeis configuráveis por evento (venda autorizada/compra/ajuste → `contabil.lancar()`). ✅ **entregue** — migração 0074 (`contabil_gatilho`), serviço `contabil_gatilhos.disparar()` conectado aos eventos (faturamento de orçamento, geração de pedidos de compra, ajuste/inventário de estoque) + painel em Configurações.
5. Homologação Focus NFe com credenciais reais (NF-e/NFC-e) — adapter + endpoints prontos em staging.

### Fiscal / Publicação (aguardam decisão do usuário)
6. Ligar `FISCAL_ENGINE_V2` em PRODUÇÃO (após deploy autorizado das releases v1.11→v2.14).
7. ~~Contract futuro: DROP físico do EAV (`variante_atributos`) e `fiscal_config` após período de coexistência.~~ ✅ **entregue (v2.26.0)** — EAV `variante_atributos` + `variantes` + `variante_produto_map` dropados na migração 0090; `fiscal_config`/`product_fiscal_profile`/`fiscal_snapshot`/`ibpt_sugestoes` tiveram a coluna renomeada para `produto_id` (0087).
8. Renomear pasta raiz para `casa-lm` (manual: fechar editores, renomear, reabrir — ambas máquinas).

### Ambiente / infra
9. `frontend/tests/` — ✅ **esqueleto entregue (v2.15.0)**: vitest + `vitest.config.ts` + `tests/format.test.ts`; script `npm test`. **Hoje: 29 testes** (ApiError/`mensagemErro`, cache/contrato runtime do client, Table/Badge). Dívida residual: testes E2E de fluxos críticos.
10. OpenAPI fase 2: ✅ **cresceu nos blueprints tocados (v2.15.0)** — estoque (`/api/estoque/saldo`), fiscal (`perfil-efetivo`) e contábil (gatilhos/lançamentos) documentados em `backend/openapi.json` (**66 paths**); segue regra de crescer por blueprint tocado.
11. **P6 — Frontend modularizado (v2.35.0/2026-08-30, validado em staging)**: **29 telas → 93 módulos** em 26 pastas (`src/pages/<tela>/`), extração verbatim sem mudança de comportamento; telas restantes sem extração viável: `categorias` (árvore de componente único), `webhooks` (componente único), `recebimento` (`ModalRecebimento` já exportado). Corrigido **mojibake** (double-encoding cp1252) em todo o frontend (dry-run = 0). Cache curto/invalidação e validação runtime mínima de contratos críticos entregues; dívida residual: virtualização de tabelas extensas e E2E.

## 11. Controle de acesso por perfil (RBAC)

**Entregue (v2.16.0)** — migração `0075_controle_acesso`. **Dívidas fechadas (v2.17.0)** — migrações `0076` (negação por usuário) e `0077` (Contract de `usuarios.perfil`). **Correção v2.20.0** — migração `0081`: `atualizacoes.visualizar` concedida a Vendedor/Estoquista/Operador (smoke test pós-deploy lê `/api/sistema/status` com perfil vendedor).

- **Modelo**: `perfis` (4 fixos: Administrador, Vendedor, Estoquista, Operador + perfis novos via CRUD), `recursos` (catálogo de módulos), `perfil_recurso` (matriz de ações), `usuario_perfis` (N:N) e `usuario_override` (`acoes_extra` concede e `acoes_negadas` nega — a efetiva é `(perfis ∪ conceder) − negar`; superuser ignora negações).
- **Ações**: `visualizar, cadastrar, editar, excluir, imprimir, aprovar, configurar`.
- **Serviço**: `catalog_server/permissao.py` — `tem_permissao()`, `exige_permissao()` (decorator), `usuario_tem_rbac()`, cache em processo TTL 30s, `definir_perfis/overrides`, `criar/atualizar/set_ativo/excluir_perfil`.
- **Gate central**: `app_factory._autorizar_acesso()` mapeia rota→recurso e método→ação (+ `_ACAO_ESPECIFICA` para config/impressão); atrás da flag `CONTROLE_ACESSO`. **Mapeamento 100%** das rotas `/api` (teste `test_mapeamento_100pct_rotas_api` garante cobertura); **deny-by-default** para rota não mapeada. Exceções: whitelist de auth (inclui webhook público `/api/webhooks/tecnospeed`), portal do fornecedor e `/api/usuarios/atual`.
- **APIs**: `api_permissoes.py` (`/api/perfis` GET/POST, `/api/perfis/<id>` PUT/DELETE, `/api/perfis/<id>/ativo` PATCH, `/api/perfis/<id>/permissoes`, `/api/permissoes/catalogo`, `/api/usuarios/<id>/perfis`, `/api/usuarios/<id>/overrides` com `conceder`/`negar`); `/api/usuarios/atual` e login devolvem `perfil_ids`, `overrides` e `permissoes`.
- **Frontend**: `src/perm.ts` (`temPermissao`), sidebar e rotas filtradas por `visualizar`, tela `#/perfis` (CRUD + matriz), cadastro de usuário multi-perfil + conceder/negar por tela, botões críticos de produtos gated.
- **Admin é superuser** (ignora checagens e negações). Presets dos demais perfis ajustáveis na tela Perfis.
- **Contract concluído**: coluna `usuarios.perfil` removida (migração 0077); RBAC via `usuario_perfis` é a fonte única. Token não carrega mais `perfil`; superuser detectado pelo vínculo ao perfil Administrador. Bootstrap do admin inicial vincula o perfil no RBAC.
- **Dívidas conhecidas (restantes)**: negação por usuário respeitada no gate (testada); CRUD de perfis pronto; permanece: token com `perfil=admin` legado ainda passa no gate (remover após período de validade dos tokens antigos).

## 12. Lifecycle orçamento→pedido + alçada de desconto (v2.18.0)

**Entregue (v2.18.0)** — migração `0078_lifecycle_pedido_alcada`.

- **Conceito (TOTVS SIGAFAT)**: orçamento = proposta editável; pedido = compromisso congelado.
- **Status**: orçamento `rascunho/ativo/em_analise/liberado` (editável até `liberado`) → pedido `finalizado/recebido/cancelado/devolvido` (congelado). `virou_pedido` marca a conversão; **`faturado` deixou de ser status** (emissão fiscal via `documentos_fiscais`).
- **Transições controladas** (`catalog_server/orcamento_status.py`): sem select livre de status. `liberado→finalizado` é a conversão (gate de alçada+estoque+fiscal, cria conta a receber e baixa estoque); `finalizado→recebido` é o caixa; **`reabrir`** (`finalizado→liberado`, exige `orcamentos.aprovar`/`autoriza_desconto`) volta para correção.
- **Editabilidade**: conteúdo (cliente/itens/desconto/condição) bloqueado após `liberado` (403). Caixa recebe apenas `finalizado`.
- **Alçada de desconto (TOTVS-like)**:
  - Desconto efetivo ≤ alçada do vendedor (`desconto_limite_pct`) → `ok`, nunca pede permissão nem expira (bug do login corrigido na v2.18.0).
  - Acima → `pendente` + 403 na conversão; `desconto_status` (`ok/pendente/aprovado/rejeitado`).
  - **Segregação**: aprovador ≠ vendedor; precisa de `autoriza_desconto` **ou** `orcamentos.aprovar`; alçada do aprovador ≥ desconto (superuser aprova tudo).
  - **Revogação**: qualquer edição de conteúdo ou `reabrir` invalida a autorização (dentro da alçada → `ok`; acima → `pendente`) com log em `desconto_aprovacao_log`.
  - **Fila do aprovador**: `GET /api/orcamentos/pendentes-aprovacao`; **rejeitar**: `POST /api/orcamentos/<id>/rejeitar-desconto` (motivo).
- **APIs**: `POST /api/orcamentos/<id>/reabrir`, `GET /api/orcamentos/pendentes-aprovacao`, `POST /api/orcamentos/<id>/rejeitar-desconto`; `PATCH` com `status` usa transições do lifecycle.
- **Frontend**: tela Orçamentos com badges de status/desconto, Autorizar/Rejeitar/Reabrir, fila de aprovação; PDV finaliza com `finalizado`; labels de alçada no cadastro de usuário.
- **Testes**: `test_alcada.py` (11) + `test_status_fluxo.py` (8) — alçada dentro/fora, segregação, revogação por edição/reabrir, rejeição, fila, transições e editabilidade.

## 13. Clientes e Fornecedores completos + trava de crédito (v2.19.0)

**Entregue (v2.19.0)** — migração `0079_clientes_fornecedores`.

### Clientes
- **Apoio comercial com selects reais**: condição de pagamento e tabela de preço por nome (via `GET /api/clientes/contexto` ampliado: vendedores + condições + tabelas + CFOP/CST/CSOSN/CEST + segmentos + categorias em uma chamada). Acabaram os inputs de ID.
- **Apoio fiscal com combos**: CFOP padrão/entrada/saída, CST ICMS/PIS/COFINS, CSOSN, CEST, alíquotas ICMS/ICMS-ST/PIS/COFINS (colunas novas: `cfop_entrada`, `cfop_saida`, `cst_csosn`, `cest`, `aliquota_icms_st`).
- **Aba Interações**: expõe a tabela `cliente_interacao` (ligação/visita/email/whatsapp/follow_up) com data do próximo contato — endpoints `GET/POST /api/clientes/<id>/interacoes` (reuso do `interacao_repo` do pós-venda).
- **Segmentação**: `segmento` (consumidor_final/profissional/construtora/revenda/varejo) + `categoria` de perfil; grid com cidade/UF, segmento e busca rápida.
- **Máscaras/validação** (`ui/format.ts`): CPF/CNPJ com dígitos verificadores, telefone/whatsapp `(11) 98765-4321`, CEP, IE; validados no salvamento (`validarDoc`).

### Fornecedores
- **CRUD completo**: razão social, CNPJ/CPF (máscara), representante, telefone, whatsapp, e-mail, endereço completo (rua/nº/bairro/cidade/UF/CEP), categoria, condição de pagamento padrão, prazo médio de entrega e avaliação (nota 1–5).
- **Aba Contatos**: tabela `fornecedor_contatos` + endpoints `GET/POST /api/fornecedores/<id>/contatos` e `DELETE /api/fornecedores/contatos/<id>`.
- **Contexto**: `GET /api/fornecedores/contexto` (categorias fixas em `repositories/suppliers.py` + condições). Busca por termo (`q`) e filtro `categoria`.
- Grid com CNPJ, cidade/UF, categoria, prazo, nota (estrelas) e busca.

### Trava de crédito no faturamento (A4)
- **Configurações > Loja**: checkboxes `bloquear_venda_sem_credito` e `bloquear_venda_com_atraso` (config_loja, mesmo padrão de `bloquear_sem_estoque`).
- **Gate na conversão orçamento→pedido** (`api_orcamentos.py`, entre alçada e estoque): bloqueia `403 {code: sem_credito | cliente_atraso}` quando a venda excede o limite disponível ou o cliente tem conta em atraso. **Cliente padrão (CONSUMIDOR, id 1) nunca bloqueia** (regra de balcão).
- `situacao_credito()` ganhou `excede_limite`/`excede_por_atraso` com `total` opcional; PDV exibe banner de aviso quando o total supera o limite.
- **Testes**: `test_credito.py` (5) + `test_fornecedores.py` (4) — dentro/fora do limite, atraso, consumidor liberado, config desligada, CRUD completo, contatos, busca e contexto. Suíte backend total: **164 testes**.

### OpenAPI
`backend/openapi.json` cresceu de 27 → 40 paths com schemas de clientes (situação, apoio comercial/fiscal, endereços, contatos, interações, contexto) e fornecedores (CRUD completo, contatos, contexto).

## 14. Compras — portal do fornecedor rico (v2.20.0)

**Entregue (v2.20.0)** — migração `0080_compras_portal` + `0081_rbac_atualizacoes_visualizar`.

### Portal do fornecedor (representante responde online)
- **Por item**: unidade de venda (UN/CX/MT/KG…, editável), quantidade por embalagem (`fator_conversao`), marca ofertada e observação — além de preço, desconto %, prazo e condição de pagamento global (que já existiam).
- **Indisponibilidade com motivo**: `em_falta_estoque | nao_trabalha_linha | descontinuado | fora_regiao | outro` (obrigatório quando marcado indisponível; vazio = disponível). `disponibilidade_estoque` segue como compat.
- **Pré-preenchimento**: a unidade/fator vêm da variante (`variantes.unidade_venda/fator_conversao`) capturados no snapshot `cotacao_itens.unidade_solicitada` no momento da cotação.
- **Bug corrigido**: `disponibilidade_estoque=0` era convertido em 1 (`or 1`) — indisponível nunca persistia.

### Comprador (Casa LM)
- **Matriz de comparação** (`montar_matriz`): cada proposta mostra unidade, fator, `qtd_embalagens` (ceil), `preco_embalagem` (preço líquido × fator), marca e o motivo quando indisponível.
- **Lembrete**: `GET /api/compras/cotacoes/<id>/lembrar/<fornecedor_id>` regenera link/whatsapp/e-mail; botão 🔔 Lembrar na tela de convites (só pendentes).
- **Pedido impresso**: coluna Unidade + nº de embalagens (ceil da quantidade/fator); marca da oferta no rodapé do item.

### Schema (migração 0080)
- `cotacao_precos` + `unidade_compra`, `fator_conversao` (default 1), `marca_ofertada`, `motivo_indisponibilidade`.
- `cotacao_itens` + `unidade_solicitada`.

### Testes
`test_compras_portal.py` (6): unidade sugerida da variante, submit com unidade/marca/motivo, motivo obrigatório p/ indisponível, matriz com preco_embalagem/qtd_embalagens, lembrete gera WhatsApp, lembrete inexistente 404. Suíte backend total: **170 testes**.

### OpenAPI
Cresceu de 40 → 43 paths com `PrecoProposta`, `Invite` e os endpoints do portal (`/api/fornecedor/<token>` e `/proposta`) e o `lembrar`.

## 15. Layout responsivo mobile/tablet (v2.20.1)

**Entregue (v2.20.1)** — melhorias de layout em `frontend/src/ui/ui.tsx`, `index.css`, `App.tsx` e telas principais.

- **Tabelas viram cards no mobile** (`< lg`): o componente `Table`/`TBody` injeta `data-label` (rótulo do cabeçalho) em cada célula; o CSS `mob-card` transforma cada `<tr>` num card empilhado com label à esquerda. Em `lg+` volta o formato de colunas. Cobre todas as listagens que usam o componente `Table` (clientes, fornecedores, financeiro, estoque, orçamentos, etc.).
- **Modal vira bottom-sheet no mobile**: abre deslizando de baixo (full-width, `rounded-t-lg`), centralizado no desktop (`sm:items-center`).
- **Abas roláveis**: `overflow-x-auto` + `whitespace-nowrap` em Clientes/Fornecedores (produtos já usava).
- **Topbar compacta**: botão Sair vira só ícone no mobile (`< sm`); título com `flex-1` e truncate.
- **Grids `grid-cols-3` puros → responsivos**: configurações de impressora, cadastro rápido de cliente no PDV e recebimento do caixa.
- **Testes**: `tests/table.test.tsx` (3) — data-label por coluna, preserva EmptyRow, classes card/coluna. Suíte frontend total: **13 testes**.

## 16. Compras — pipeline único (modelo TOTVS) (v2.21.0)

**Entregue (v2.21.0)** — remove a confusão conceitual Cotação × Compras.

### Conceito (referência TOTVS Protheus SIGACOM)
Cadeia linear de documentos: **Solicitação de Compra → Cotação (negociação/propostas) → Análise (vencedor) → Pedido de Compra → Recebimento**. Cotação **não é módulo separado** — é etapa do processo de compras; Pedido de Compra é o compromisso formal.

### Mudanças
- **Módulo Compras único** (`#/compras`): abas **Nova cotação / Cotações / Pedidos de compra**.
- **Aba Cotações**: lista todas as cotações (status normalizado `aberta→Pendente`, `fechada→Finalizada`), botão Abrir para continuar no fluxo.
- **Aba Pedidos de compra**: lista `pedidos_compra` com status (Enviado/Recebido), botão **Receber** (entrada de estoque + conta a pagar + status recebido) e PDF.
- **Menu**: removidas as rotas avulsas `#/cotacoes` e `#/solicitacoes` do menu lateral — tudo passa por Compras. As telas legadas continuam acessíveis por URL (compat).
- **Endpoint novo**: `POST /api/compras/pedidos/<id>/receber`; `GET /api/solicitacoes-compra/<id>` (detalhe com itens) para futura "cotar a partir da solicitação".
- **Bug corrigido**: `confirmar_recebimento` usava `item.get()` sobre `PgRow` (PostgreSQL) — recebimento falhava.

### Testes
`test_pedidos_compras.py` (4): listar pedidos, receber atualiza status/estoque, receber duas vezes bloqueia (400), solicitação detalhe com itens. Suíte backend total: **174 testes**.

### OpenAPI
Cresceu de 43 → 45 paths (`receber` pedido, `solicitacoes-compra/<id>`).

## 17. Vendas a prazo — parcelas e boleto (v2.22.0)

**Entregue (v2.22.0)** — migração `0082_boletos_receber`.

### Contas a receber por parcela
- Ao finalizar (`finalizado`), gera **contas a receber por parcela** conforme a condição de pagamento (`condicao_parcelas`: dias + percentual), **somente quando**: cliente **identificado** (não é o CONSUMIDOR id 1) **e** condição **ativa**.
- Condição à vista / sem parcelas / cliente padrão → mantém **1 conta** e recebimento no **caixa** (balcão).
- Ajuste da última parcela quando os percentuais não somam 100%.
- **Reabrir** (sem boleto) **estorna** as contas a receber; **cancelar** já cancelava (via documento).
- `orcamento_repo.listar` agora devolve `condicao_nome` e `n_parcelas` (contas abertas do documento).

### Boleto
- `POST /api/orcamentos/<id>/boleto` gera boletos das parcelas (linha digitável 48 + código de barras genérico, **sem integração bancária real nesta fase**).
- `GET /orcamentos/<id>/boleto` imprime o template `boleto_print.html` (1 boleto por parcela) com **assinatura do cliente/autorizado**.
- **Trava**: pedido `finalizado` com boleto emitido **não pode ser reaberto/alterado**.
- Migração 0082: `contas_receber` + `status_boleto`, `linha_digitavel`, `codigo_barras`, `nosso_numero`, `url_boleto`.

### Frontend (Orçamentos)
- Lista: pedido `finalizado` **a prazo** (n_parcelas>1) mostra **Boleto** e **Contas** (link Financeiro), **sem** "Receber"; à vista mantém "Receber" (caixa).
- Detalhe: mostra condição de pagamento e nº de parcelas; ações condicionadas ao tipo.
- Impressão do pedido de venda (`orcamento_print.html`) com campo **"Cliente / autorizado — de acordo"**.

### Testes
`test_parcelas_boleto.py` (5): parcelas por condição, consumidor não gera, boleto marca parcelas, reabrir com boleto bloqueia, reabrir sem boleto estorna. Suíte backend total: **180 testes**.

## 18. Integração de pagamentos nas contas a receber (v2.23.0 · v2.24.0)

**Entregue (v2.23.0)** — migração `0083_payment_providers`. **Fase 1**: Asaas + Mercado Pago (sandbox). **Fase 2 (v2.24.0)**: EfiPay + Sicoob.

### Conceito
Boleto e PIX são emitidos **a partir da conta a receber** (Financeiro), via **provedor escolhido por prioridade de custo** configurável por operação (boleto/pix) e ambiente (sandbox/produção). Troca de provedor = reordenar prioridade, sem código.

### Backend (`catalog_server/payments/`)
- `base.py` (interface), `registry.py` (seleção por prioridade), `repo.py` (config), `asaas.py` + `mercadopago.py` (fase 1), `efipay.py` + `sicoob.py` (fase 2), `service.py` (emissão + baixa automática).
- **EfiPay**: OAuth2 client credentials + certificado P12/PEM (mTLS) p/ PIX (`POST /v2/cob`) e boleto via API de cobranças (`POST /v1/charges`); webhook `pix.received`/`charge`.
- **Sicoob**: sandbox com token Bearer de teste + header `client_id`; produção com OAuth2 + certificado ICP-Brasil; boleto Cobrança V3 (`/cobranca-bancaria/v3/boletos`) e PIX (`/pix/api/v2/cob`); webhook `pix`.
- `POST /api/financeiro/receber/<id>/cobranca` (boleto/pix); `GET .../cobranca/status`; `POST .../comprovante` (upload depósito/TED).
- `POST /api/webhooks/payments/<provider>` (whitelist pública) → valida evento → **baixa automática** idempotente (`webhook_id`).
- `POST /api/financeiro/receber/<id>/receber` ampliado com `forma_pagamento` (dinheiro/pix/cheque/deposito_bancario/ted/transferencia/cartão), lança no caixa.
- `GET/PUT /api/payment-providers(/config)`.

### Schema (migração 0083)
- `payment_provider` (catálogo: asaas/mercadopago/efipay/sicoob), `payment_provider_config` (credenciais + operacao + ambiente + prioridade + ativo).
- `contas_receber` + `provider_id`, `payment_id`, `tipo_cobranca`, `status_cobranca`, `payload_pix`, `qr_code_base64`, `txid`, `webhook_id`, `ultima_consulta_em`.
- `conta_comprovante` (comprovante de depósito/TED na baixa manual).

### Frontend
- **Configurações → Integrações de pagamento**: credenciais por provedor/operação/ambiente + prioridade de custo + ativo.
- **Financeiro → Contas a Receber**: coluna Cobrança (badge status), botões **Boleto / PIX** (mesma parcela), modal com QR code/copia-e-cola e boleto/URL; modal **Receber** com forma de pagamento + anexo de comprovante (depósito/TED obrigatório).

### Testes
`test_payments.py` (7): configurar provedor, emitir boleto Asaas (mock), webhook baixa automática idempotente, receber manual com forma, comprovante, emitir boleto EfiPay, emitir PIX Sicoob + webhook. Suíte backend total: **187 testes**.

## 19. Financeiro: parcelamento, recorrência e origem (v2.25.0)

**Entregue (v2.25.0)** — migração `0084_lancamentos_lote`.

### Conceito (TOTVS/desdobramento FINA050/FINA040)
1 lançamento → N títulos com vencimentos diferenciados. Toda parcela de um lançamento compartilha `grupo_id` e carrega `parcela i/N` + `origem_tipo/origem_id`.

### Backend
- `services/lancamentos_lote.py`: `calcular_parcelas` (`condicao` usa `condicao_parcelas` dias/percentual; `manual` nº+intervalo; `datas` explícita), `calcular_recorrencia` (mensal/semanal/anual, **todas as ocorrências geradas antecipadamente**), `criar_lote`, `excluir_lote` (só abertas), `listar_lote`.
- Endpoints: `POST /api/financeiro/{pagar|receber}/lote`, `POST /api/financeiro/lote/preview` (não grava), `GET/DELETE /api/financeiro/lote/{tabela}/{grupo_id}`, `POST/GET /api/financeiro/anexo/{tabela}/{conta_id}` (tabela `conta_anexo`).
- **Compras → Financeiro**: `confirmar_recebimento` aceita `condicao_pagamento_id` — com parcelas, gera contas a pagar **parceladas** com `origem_tipo='pedido_compra'`, `origem_id`, `grupo_id`; sem, 1 conta em 30 dias (comportamento anterior + origem).
- **Vendas a prazo (v2.22)**: parcelas ganham `origem_tipo='venda'`, `origem_id`, `grupo_id`, `parcela i/N`.

### Frontend
- **Financeiro (Pagar e Receber)**: modal `ModalLancamento` com seção Parcelamento — À vista | Por condição (select + **preview das parcelas**) | Parcelado (nº + intervalo) | Recorrente (frequência + ocorrências + dia). Grid com coluna **Parcela (1/3)**, badge de recorrência, **origem clicável** (Pedido → Compras) e 🗑 excluir parcelas em aberto do grupo. 📎 anexo de nota/boleto por lançamento.
- **Compras → Receber pedido**: modal com select de condição + **preview das parcelas** antes de confirmar (não mais silencioso); resultado informa nº de contas geradas.

### Testes
`test_lancamentos_lote.py` (7): parcelamento por condição (30/60/90, ajuste de arredondamento na última), manual (n+intervalo), recorrência mensal antecipada, preview não grava, exclusão de grupo preserva pagas, pedido parcelado com origem, venda a prazo com grupo. Suíte backend total: **194 testes**.

### OpenAPI
Cresceu de 51 → 56 paths (lote pagar/receber, preview, ver/excluir grupo, anexo).

## 20. Unificação produto/variante (v2.26.0)

**Entregue (v2.26.0)** — migrações `0085_produto_unificado_expand` → `0090_produto_unificado_contract`.

### Conceito
Cada antiga `variantes` virou um **produto independente** em `produtos_cadastro` (Opção A). A tabela `variantes`, o EAV `variante_atributos` e a tabela de apoio `variante_produto_map` foram **eliminadas**. Não há mais editor de variações no cadastro: o produto carrega seus próprios dados operacionais e atributos.

### Banco (cadeia Expand→Migrate→Contract)
- **0085 (Expand)**: `produtos_cadastro` ganhou colunas operacionais (sku, ean, preco, preco_promocional, old_price, pix_price, custo_unitario, preco_venda, ncm, peso, dimensoes, unidade_venda, embalagem, fator_conversao, localizacao, unidade_tributavel) + backfill da variante principal.
- **0086 (Migrate)**: criou `variante_produto_map` (62.731 linhas) + **3.048 produtos novos** para as variantes extras (total 62.731).
- **0087 (Reapontamento)**: `variante_id` → `produto_id` em ~20 tabelas de negócio (idempotente; técnica de offset p/ preservar constraints únicas no espaço compartilhado de ids; mescla de `estoque_saldo` somando quantidades).
- **0088 (Atributos)**: valores do EAV movidos para `produtos_cadastro.atributos` (JSONB por nome).
- **0089 (Funções)**: `reconciliar_estoque()` recriada com `produto_id`.
- **0090 (Contract)**: `DROP` de `variantes`, `variante_atributos`, `variante_produto_map` (destrutiva; backup pré-aplicação; `backward` requer restore).

### Backend
- `repositories/produtos.py`: CRUD unificado (criar/editar produto com `dados` operacionais + `atributos` por nome); sem `_replace_variantes`/`find_or_create_variant`. `get_product` devolve `atributos` = **definições da família** e `atributos_valores` = **valores por nome**.
- Repos/services/blueprints reescritos para `produto_id` (estoque, preços, fiscal, compras, loja, catálogo, quotes, importar_catalogo, fts, abc, categorias). Nenhuma referência SQL a `variantes` restante.
- Catálogo (`repositories/catalog.py`) é **flat**: um card por produto (`group:false`, `price` único), sem matriz de variações.

### Frontend
- `produtos.tsx`: aba/editor de **Variações removido**; formulário edita o produto diretamente + atributos por nome.
- `catalogo.tsx`: cards unitários (sem `GroupCard`/`ModalVariante`/matriz 2D).
- `cart.ts`: chaves do carrinho por `produto_id`; `addCustomItem` sem `produto_pai`/atributos.
- `client.ts`: `ProdutoCadastro`/`ProdutoCadastroPayload` sem `variantes[]`; leituras `produto_id`.
- Relabels "variante"→"produto" nas telas secundárias.

### Testes
Backend **236 testes** verdes. Frontend: typecheck + 27 testes + build verdes. O estado atual inclui outbox com claim/lease (0102), transações conta+caixa e isolamento de TLS do staging; a validação desta correção foi feita em DEV, sem deploy.
