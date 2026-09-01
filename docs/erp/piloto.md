# Piloto (Onda 12) — prontidão e plano de implantação

Base: `PLANO_MESTRE_IMPLEMENTACAO_ERP.md` (§20 Piloto) + `AGENTS.md` (regra de
publicação: **nenhum deploy sem confirmação explícita**).

## PIL-001 — Checklist P0 (gate de produção)

### Banco / migrações
- [x] Migrações versionadas com `VERSION/RISCO/NAME/MUDANCA/guard/forward/backward`
- [x] Banco vazio→head e incremental→head verdes (conftest drops schema e aplica todas)
- [x] `AUTO_MIGRATE=0` em produção + advisory lock; migração nunca dentro do `compose up`
- [x] Backup antes de migration relevante (pipeline)

### Backend / API
- [x] RBAC deny-by-default com mapeamento 100% das rotas `/api` (teste `test_mapeamento_100pct_rotas_api`)
- [x] Contrato JSON estável (`error`, `code`) sem stack/segredo; auditoria por evento (ARC-006)
- [x] Idempotência transversal (ARC-003) + locks `FOR UPDATE`/advisory (ARC-004)
- [x] Reconciliação de divergências (ARC-005) + OpenAPI (114 paths)

### Frontend
- [x] typecheck + build + 34 testes Vitest; teclado PDV contratado (`docs/erp/contracts/teclado-pdv.md`)
- [x] Tabela Lightning/SLDS (mob-card, `data-label`, navegação por teclado)

### Estoque / venda / financeiro
- [x] Ledger de fatos idempotente + estorno (EST-002/003); disponibilidade única (EST-001)
- [x] Sessão de caixa com fechamento/diferença (VEN-004); pagamentos múltiplos idempotentes (VEN-003)
- [x] Crédito com trava (A4) + cobrança/renegociação (VEN-006)
- [x] Custo médio por depósito (DECISAO-002) alimentando CMV/DRE (BI)

### Compras / recebimento
- [x] Solicitação→cotação→comparação→aprovação→pedido→recebimento (COM/Onda 4)
- [x] Recebimento com conferência parcial + três vias + NF XML + postagem idempotente (REC-001..005)

## PIL-002 — Evidências operacionais P1

- Backend: **505 testes** verdes em PostgreSQL real (`TEST_PG_URL`)
- Frontend: typecheck/build/34 testes verdes
- Schema DEV: **141** (89 migrações aplicadas)
- Endpoints críticos validados localmente (health 200; rotas respondem 401 sem token)

## PIL-003 — Ações antes da publicação

1. **Fiscal (externa)**: homologação FOCUS com credenciais reais (cert A1/A3 + contador)
   — matriz fiscal aprovada (FIS-001); DECISAO-003 (Simples Nacional).
2. **Ambiente**: STAGING (`siscom-staging`) recebe a branch via workflow **Deploy Staging**
   (banco nasce vazio → migra → smoke tests).
3. **Imagens (P8)**: executar limpeza/backfill de imagens após aprovação.
4. **Release manifest**: `releases/vX.Y.Z.json` com mapa técnico (imagens/migration/API/features).
5. **Rollback 2 dimensões**: dump pré-migração + imagens `prev`.

## PIL-004 — Aprovação explícita

- [ ] Usuário autoriza o deploy de STAGING da branch validada
- [ ] Usuário autoriza PRODUÇÃO (v2.32.2 atual) após validação em staging
- [ ] Contador valida DRE/exportação e matriz fiscal antes de liberar emissão real

**Status: aguardando decisões do usuário** (fiscal, imagens, publicação). Nenhum
deploy foi disparado.