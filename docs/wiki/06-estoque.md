# Estoque e qualidade do catálogo

## Estoque (`#/estoque`)

**O que é?** Controle de saldo e fatos de estoque por depósito. **Para que
serve?** Consultar disponibilidade, movimentar, inventariar, expedir e decidir
compras. **Papel:** garante que venda e compra reflitam o físico.

1. Selecione o depósito.
2. Consulte **Saldo** por produto e situação.
3. Use **Movimentos/Kardex** para encontrar a origem de uma diferença.
4. Execute **Inventário** com contagem e justificativa.
5. Analise **ABC**, reposição, trânsito e expedição.

Use **Depósitos**, **Endereços**, **Lotes** e **Inventário cíclico** conforme a
operação. Nunca altere saldo por fora de um fato auditável.

## Qualidade do Catálogo (`#/diagnostico-variacoes`)

**O que é?** Diagnóstico de variações inconsistentes. **Para que serve?** Corrigir
atributos faltantes, duplicidades e dados que impedem venda, compra ou fiscal.
Abra o problema, corrija no cadastro mestre e execute nova análise.

## Quem pode usar?

Estoquista registra/conferre; gestores analisam ABC e reposição; ajustes e
inventários dependem do RBAC.

## Auditoria

Entrada de compra, saída de venda, ajuste, inventário, lote, endereço e
expedição precisam de origem, operador, depósito e data.
