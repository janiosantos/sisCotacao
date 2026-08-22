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
| 03 | Todo container → versão/tag (`backend:vX.Y.Z`, não só `latest`) | ⚠️ a implementar |
| 04 | Todo endpoint importante → contrato documentado (hoje: interfaces TS do `client.ts`; meta: OpenAPI) | ⚠️ parcial |
| 05 | Mudança incompatível → Expand/Contract (ciclo A–F) | ✅ regra vigente |
| 06 | Migration → testada automaticamente (banco vazio→head e N→head; hoje: E2E manual com Postgres descartável) | ⚠️ parcial |
| 07 | Produção → nunca alteração manual de schema | ✅ (`AUTO_MIGRATE=0` + advisory lock) |
| 08 | Frontend → nunca acesso direto ao PostgreSQL | ✅ |
| 09 | Migration destrutiva → somente após período de compatibilidade | ✅ (etapa F) |
| 10 | Toda release → plano de rollback nas duas dimensões (app × banco) | ✅ |
| 11 | Produção → backup antes de migration relevante | ✅ (pipeline) |
| 12 | Deploy → health check + smoke test | ⚠️ health ✅ / smoke ❌ |

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

DEV (diário) → **STAGING** (cópia estrutural de produção; testa Migration+Backend+Frontend juntos, com dados representativos) → PRODUÇÃO (só recebe release aprovada).

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
2. Smoke tests no pipeline
3. CI com testes automatizados (inclui testes de migration automáticos)
4. STAGING
5. OpenAPI (contrato formal da API)
6. Infraestrutura de feature flags

> Até as dívidas fecharem, substituto mínimo aceitável: E2E local com Postgres descartável + validação live pós-deploy dos endpoints afetados (prática das releases v1.6.x).
