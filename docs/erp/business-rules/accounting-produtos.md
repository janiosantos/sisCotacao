# Regras de Negócio — Contabilidade

Vendas, compras, recebimentos, pagamentos, movimentos de estoque e documentos fiscais podem gerar BusinessEvent. O evento é contabilizado pela PostingRule vigente para empresa, operação, produto/categoria, centro de custo e período.

O sistema deve impedir lançamento desequilibrado, duplicado ou em período fechado. Correções devem produzir estorno e novo lançamento, mantendo a cadeia de auditoria.
