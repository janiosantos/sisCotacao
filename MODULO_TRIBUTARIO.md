# MODULO_TRIBUTARIO.md — Diretrizes Gerais do ERP

## Objetivo

ERP comercial modular para varejo de materiais elétricos, hidráulicos, ferramentas, ferragens e materiais de construção.

## Regras permanentes

1. Não inventar regras de negócio, fiscais ou integrações.
2. Não hardcodar regras tributárias.
3. Toda alteração de schema exige migration.
4. Dados fiscais, financeiros e documentos autorizados devem preservar histórico.
5. Backend/domínio é autoridade de negócio; frontend não calcula tributos.
6. Dinheiro e tributos usam Decimal/NUMERIC.
7. Features relevantes exigem testes e documentação.
8. Em dúvida fiscal, usar `FISCAL_REVIEW_REQUIRED` em vez de assumir.
9. Não alterar produção manualmente como procedimento normal.
10. Antes de implementar, identificar impactos em banco, backend, frontend, estoque, financeiro e fiscal.

## Skills obrigatórias por domínio

- Fiscal MG: `.agents/skills/fiscal-mg/SKILL.md`
- Motor fiscal: `.agents/skills/fiscal-engine/SKILL.md`
- Banco: `.agents/skills/database/SKILL.md`
- Backend/API: `.agents/skills/api-backend/SKILL.md`
- Frontend: `.agents/skills/frontend/SKILL.md`
- Testes: `.agents/skills/testing/SKILL.md`
- Deployment: `.agents/skills/deployment/SKILL.md`

## Workflows

- Nova feature: `.agents/workflows/feature.md`
- Regra fiscal: `.agents/workflows/fiscal-rule.md`
- Migration: `.agents/workflows/migration.md`
- Release: `.agents/workflows/release.md`

## Princípio

O sistema deve conseguir explicar por que uma operação recebeu determinada tributação, qual regra/versionamento foi utilizado e qual fundamento foi considerado.
