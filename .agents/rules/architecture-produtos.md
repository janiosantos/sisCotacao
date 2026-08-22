# Regra de Arquitetura

Manter separação de responsabilidades entre domínio comercial, classificação fiscal, parametrização tributária, cálculo e documento fiscal.

## Camadas

| Camada | Responsabilidade | Exemplos |
|---|---|---|
| Produto | Identidade e classificação compartilhada | NCM, CEST, origem, marca, unidade |
| Variação/SKU | Unidade comercial diferenciada | SKU, GTIN/EAN, atributos, preço, custo, estoque |
| TaxRule/FiscalProfile | Regra contextual e versionada | regime, operação, UF, CFOP, CST/CSOSN, ICMS, PIS/COFINS, ST |
| InvoiceItem | Snapshot do resultado | base, alíquota, valores e códigos efetivamente aplicados |
| IBPTTable | Tabela externa versionada | NCM/NBS, percentuais, vigência e fonte |

Preferir composição e políticas explícitas a condicionais espalhadas pela aplicação. Toda decisão arquitetural relevante deve gerar um registro em `docs/fiscal/decisoes/`.
