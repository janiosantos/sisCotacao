# ADR 0002 — Validação Normativa Contínua

## Status

Proposto

## Decisão

A base fiscal do ERP não tratará exemplos de códigos, alíquotas ou fórmulas como regras universais. Toda parametrização definitiva deverá apontar para fonte oficial e vigência.

## Motivo

Legislação estadual, convênios, ajustes, notas técnicas e regras de documentos fiscais mudam ao longo do tempo. O software precisa distinguir conhecimento de engenharia de regra jurídica vigente.

## Consequência

O agente deve marcar `FISCAL_REVIEW_REQUIRED` sempre que não conseguir determinar a regra vigente com segurança suficiente.
