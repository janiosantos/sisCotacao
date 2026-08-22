# Modelo de Entidades

```text
Product
 ├─ classificação: NCM, CEST, origem, marca, categoria, unidade
 ├─ 1:N ProductVariant
 └─ 0:N TaxRule

ProductVariant
 ├─ SKU, GTIN/EAN, attributes, custo, preço, estoque
 └─ 0:N TaxRule override

TaxRule
 ├─ contexto: regime, operação, UFs, finalidade, cliente, vigência
 ├─ saída: CFOP, CST/CSOSN, ICMS, PIS/COFINS, ST etc.
 └─ versão e fonte

InvoiceItem
 └─ snapshot dos valores e códigos efetivamente aplicados

IBPTTable
 └─ dados versionados por NCM/NBS e vigência
```

A precedência recomendada é: override ativo e compatível da Variação; regra ativa e compatível do Produto; caso contrário, pendência ou bloqueio.
