# PROBLEM
- **Severidade:** alta
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/services/relatorios_operacionais.py:102-190`

## Explicação para leigos
O relatório analítico de vendas pode mostrar custo e margem errados quando o mesmo produto aparece em mais de uma linha do mesmo pedido.

## Evidência e análise técnica
Na CTE `custo`, o CMV é agregado por `(origem_id, produto_id)`. Na CTE `linhas`, as linhas são agrupadas por pedido e produto, mas também por vários atributos da linha, como nome, SKU e marca. Se o mesmo produto tiver duas linhas com atributos diferentes, haverá duas linhas em `linhas`. O `LEFT JOIN custo` repete o mesmo valor agregado para cada uma delas e o `SUM(COALESCE(c.cmv,0))` da CTE `agregado` soma o custo mais de uma vez.

## Impacto
Margem bruta, CMV e decisões de preço/compras podem ficar artificialmente piores. O erro aparece apenas em certos pedidos, o que torna a inconsistência difícil de perceber sem conciliação com o ledger de estoque.

## Solução proposta
Agregar primeiro as linhas de venda na mesma granularidade do custo, ou distribuir o CMV por linha antes da agregação. Garantir que cada movimento de saída seja contado uma única vez por item de venda e criar uma consulta de reconciliação `CMV do relatório = soma do ledger` para períodos e pedidos com produto repetido.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ relatorios_operacionais.py
-SUM(COALESCE(c.cmv,0)) AS cmv
+SUM(COALESCE(c.cmv_por_linha,0)) AS cmv
+-- ou juntar custo depois de consolidar uma única linha por pedido/produto
```

