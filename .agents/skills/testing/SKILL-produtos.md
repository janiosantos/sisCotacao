---
name: testing
description: Definir testes unitários, integração, contrato, regressão e cenários fiscais para garantir cálculos determinísticos e preservação histórica. Usar em qualquer mudança fiscal ou de emissão.
---

# Testing

Criar matriz de cenários com regime, operação, UFs, finalidade, cliente, vigência, produto, variação e override. Testar ausência de regra, conflito, mudança de versão, arredondamento, idempotência e snapshot do InvoiceItem.

Manter casos reais anonimizados e fixtures com fonte. Não usar alíquotas fictícias em testes que pretendam validar regra legal; separar testes de infraestrutura dos testes de conteúdo fiscal.
