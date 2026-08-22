# ERP Casa LM — Produtos, Estoque, Contabilidade e Fiscal

Este pacote define a base de negócio para um ERP que cadastra produtos e variantes, usa atributos flexíveis em JSONB, controla estoque por movimentos e integra regras fiscais, contabilidade e emissão de documentos eletrônicos.

## Módulos

| Módulo | Responsabilidade | Entidades principais |
|---|---|---|
| Catálogo | Produto, variante, atributos e classificação | Product, ProductVariant, AttributeDefinition |
| Comercial | Preço, custo, venda, compra e devolução | PriceList, Sale, SaleItem, Purchase |
| Estoque | Saldos, reservas, depósitos e movimentos | Warehouse, StockBalance, StockMovement, StockReservation |
| Fiscal | Regras, snapshots, documentos e eventos | TaxRule, FiscalDocument, FiscalItem, FiscalEvent |
| Contabilidade | Plano, matrizes, partidas e períodos | Account, PostingRule, JournalEntry, JournalLine |
| Integrações | SEFAZ, certificados, filas e protocolos | IntegrationAttempt, FiscalProtocol |

A separação central é: Produto define a mercadoria; Variante define a unidade comercial; estoque registra fatos; TaxRule resolve o contexto; FiscalItem preserva o resultado; JournalEntry registra o efeito contábil.
