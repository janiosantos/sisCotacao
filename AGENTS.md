# AGENTS.md

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
1. **Indicador de completude** em Dados Gerais (obrigatórios preenchidos × pendentes).
2. **Estoque por depósito + situação** (ok/ruptura/excesso) na tabela da aba Variações.
3. **Perfil Fiscal**: mostrar herdado do produto vs override por variação (hierarquia v2.5.0) + validação inline (marca, formato NCM, preço>0).

### Estoque / Contábil
4. **v2.15.0**: gatilhos contábeis configuráveis por evento (venda autorizada/compra/ajuste → `contabil.lancar()`) — `lancar()` já existe, falta conectar aos eventos.
5. Homologação Focus NFe com credenciais reais (NF-e/NFC-e) — adapter + endpoints prontos em staging.

### Fiscal / Publicação (aguardam decisão do usuário)
6. Ligar `FISCAL_ENGINE_V2` em PRODUÇÃO (após deploy autorizado das releases v1.11→v2.14).
7. Contract futuro: DROP físico do EAV (`variante_atributos`) e `fiscal_config` após período de coexistência.
8. Renomear pasta raiz para `casa-lm` (manual: fechar editores, renomear, reabrir — ambas máquinas).

### Ambiente / infra
9. `frontend/tests/` ainda sem suíte (vitest) — criar esqueleto quando priorizado.
10. OpenAPI fase 2: cresce por blueprint tocado (regra vigente).