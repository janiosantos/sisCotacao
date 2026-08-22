# ADR 0002 — ERP Integrado por Eventos e Snapshots

**Status:** proposto

## Decisão

Adotar catálogo separado de estoque, fiscal e contabilidade. Usar movimentos imutáveis para estoque, TaxRule contextual para fiscal, snapshots em FiscalItem e eventos idempotentes para contabilização.

## Motivo

Essa separação evita que alterações cadastrais ou de regras reescrevam fatos históricos, reduz acoplamento entre módulos e permite reprocessamento seguro de integrações.

## Consequências

Será necessário manter versionamento, chaves de idempotência, reconciliação de saldos, auditoria, estados de documento e matrizes contábeis. A parametrização de códigos, alíquotas e contas deve ser validada pelos responsáveis fiscal e contábil.
