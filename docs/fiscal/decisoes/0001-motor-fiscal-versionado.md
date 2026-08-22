# ADR 0001 — Motor Fiscal Versionado

## Status

Proposto

## Contexto

O ERP precisa suportar alterações frequentes de legislação sem alterar a interpretação histórica de documentos já emitidos.

## Decisão

O motor fiscal utilizará regras versionadas por vigência. O resultado aplicado a cada documento fiscal será persistido como snapshot.

## Consequências

- Regras atuais podem mudar sem alterar documentos históricos.
- Auditoria pode identificar a regra utilizada.
- Alterações fiscais exigem testes de regressão.
- O banco terá maior estrutura de versionamento.

## Regras relacionadas

- `.agents/rules/fiscal.md`
- `.agents/skills/fiscal-engine/SKILL.md`
