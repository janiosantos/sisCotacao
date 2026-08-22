# Modelo de Banco de Negócio

## Entidades nucleares

```text
Company 1:N Product 1:N ProductVariant
Product 1:N TaxRule; ProductVariant 0:N TaxRuleOverride
ProductVariant 1:N StockMovement; Warehouse 1:N StockMovement
ProductVariant 1:N Price; ProductVariant 1:N StockBalance
Sale 1:N SaleItem; FiscalDocument 1:N FiscalItem
FiscalDocument 1:N FiscalEvent; FiscalDocument 0:N IntegrationAttempt
BusinessEvent 1:N JournalEntry 1:N JournalLine
```

## Campos recomendados

| Entidade | Campos estruturais | Campos flexíveis/auditáveis |
|---|---|---|
| Product | id, company_id, name, brand_id, category_id, NCM, CEST, origin, unit_id, status | metadata JSONB, audit timestamps |
| ProductVariant | id, product_id, SKU, GTIN, barcode, status | attributes JSONB, dimensions JSONB |
| StockMovement | id, variant_id, warehouse_id, type, quantity, unit, occurred_at, source | lot/serial JSONB quando necessário |
| StockBalance | variant_id, warehouse_id, physical, reserved, available, blocked, in_transit | reconciliation metadata |
| TaxRule | contexto, vigência, prioridade, versão, outputs fiscais | conditions JSONB controlado |
| FiscalItem | documento, variant, descrição, quantidade, preço, bases, alíquotas, valores | snapshot JSONB imutável |
| JournalEntry | company, period, source, date, status | metadata de integração |
| JournalLine | entry, account, debit, credit, cost_center | dimensions JSONB validado |

## Invariantes

SKU único por empresa; quantidades positivas no movimento com direção explícita; saldo disponível reconciliável; TaxRule com vigência não sobreposta para a mesma chave/prioridade; FiscalItem imutável após autorização; JournalEntry equilibrado; nenhum lançamento em período fechado sem estorno aprovado.

## JSONB

Usar JSONB para atributos que variam por categoria, mas manter `AttributeDefinition` para validar tipo, unidade, valores aceitos e obrigatoriedade. Criar índices GIN ou projeções apenas para consultas justificadas. Não colocar em JSONB chaves que precisem de FK, unicidade, auditoria detalhada ou cálculo crítico.
