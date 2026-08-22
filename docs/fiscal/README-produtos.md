# Documentação Fiscal — Casa LM

Esta pasta concentra conhecimento fiscal necessário para construir o cadastro de produtos, o motor tributário e a futura emissão de NF-e/NFC-e com atenção a Minas Gerais. O conteúdo deve distinguir fato confirmado, hipótese, decisão de arquitetura e regra dependente de fonte externa.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `legislacao/` | Cópias ou referências controladas de normas e atos oficiais |
| `regras/` | Regras de negócio e matrizes de decisão |
| `cenarios/` | Casos de uso e exemplos de operações |
| `calculos/` | Fórmulas, precisão, arredondamento e invariantes |
| `decisoes/` | ADRs e decisões com contexto, alternativas e consequências |

## Arquitetura fiscal adoptada

O Produto Base mantém classificação compartilhada, como NCM, CEST, origem, marca, categoria e unidade. A Variação mantém SKU, GTIN/EAN, atributos técnicos, custo, preço e estoque. TaxRule/FiscalProfile concentra a parametrização contextual, podendo existir no Produto e ser sobrescrita na Variação quando justificado. InvoiceItem guarda o snapshot do resultado efetivamente aplicado. IBPTTable é uma tabela central versionada por NCM/NBS e vigência, não uma característica permanente da variação.

## Controle de fontes

Cada regra deve indicar fonte, versão, data de consulta, vigência, responsável pela revisão e status. Informações não validadas não devem ser usadas para emissão em produção.

## Aviso

Esta documentação é orientação de engenharia e não substitui validação por profissional habilitado ou consulta à documentação oficial aplicável.
