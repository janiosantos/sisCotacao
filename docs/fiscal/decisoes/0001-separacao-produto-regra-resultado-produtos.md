# ADR 0001 — Separar Produto, Regra e Resultado

**Status:** aceite

## Contexto

A tributação depende do contexto da operação e não deve ser tratada como atributo fixo de cada SKU. O histórico da NF deve permanecer estável mesmo quando regras futuras mudarem.

## Decisão

Adotar quatro camadas: Produto Base, ProductVariant, TaxRule/FiscalProfile e InvoiceItem. Manter IBPTTable separada e vinculada por NCM/NBS. Permitir override de TaxRule na Variação apenas quando necessário.

## Consequências

A solução reduz duplicação, permite operações internas e interestaduais e preserva rastreabilidade. Em contrapartida, exige resolução contextual, versionamento, testes de precedência e uma interface que explique a origem do valor.

## Riscos e controles

O risco de parametrização incompleta será tratado com status `PENDENTE` ou `BLOQUEADO`, alertas e revisão fiscal. O risco de alteração histórica será mitigado pelo snapshot em InvoiceItem.

## Base da decisão

A decisão foi consolidada a partir do material fornecido pelo solicitante em `pasted_content.txt`, especialmente a recomendação de não colocar toda a tributação no Produto Base nem toda na Variação. Códigos e alíquotas concretos permanecem dependentes de validação documental.
