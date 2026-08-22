---
name: fiscal-engine
description: Projetar, implementar e testar resolução de TaxRule/FiscalProfile e cálculo de tributos com versionamento, herança Produto → Variação e snapshot no InvoiceItem. Usar quando houver mudança em regras ou cálculos fiscais.
---

# Fiscal Engine

## Contrato conceitual

Entrada: Produto, Variação, empresa, regime, operação, UF origem/destino, cliente, finalidade, data de operação e flags fiscais.

Processamento: validar entrada, selecionar regras vigentes, resolver override, calcular bases e valores com precisão decimal, aplicar arredondamento documentado e gerar avisos.

Saída: códigos aplicados, bases, alíquotas, valores, regra/versão, evidências e status (`RESOLVIDO`, `PENDENTE`, `BLOQUEADO`).

Não retornar zero silenciosamente quando faltar parametrização. Testar invariantes, arredondamento, vigência, conflitos e reprocessamento.
