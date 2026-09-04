# PROBLEM
- **Severidade:** média
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/services/relatorios_operacionais.py:210-246`, `backend/catalog_server/services/relatorios.py:149-160`

## Explicação para leigos
O relatório analítico de compras filtra diretamente o campo `data_pedido`, mas o próprio sistema reconhece que pedidos antigos podem ter data de geração ou data de criação no lugar dele. Esses pedidos ficam fora do relatório mesmo existindo.

## Evidência e análise técnica
`compras_analitico()` começa com `where = ["data_pedido BETWEEN ? AND ?"]`. Na CTE `linhas`, entretanto, a data exibida é `COALESCE(pc.data_pedido::date, pc.data_geracao::date, pc.criado_em::date)`. O relatório sintético usa a mesma regra de `COALESCE` na filtragem. Portanto, os dois relatórios do mesmo domínio podem retornar totais diferentes para o mesmo período.

## Impacto
Compras históricas, lead time, valores por fornecedor e pendências podem desaparecer da visão analítica. A administração pode comparar números incompatíveis entre telas e tomar decisões baseadas em dados incompletos.

## Solução proposta
Definir uma única data de negócio para o relatório, preferencialmente uma expressão nomeada na CTE, e reutilizá-la em filtros, ordenação e exportação. Criar backfill idempotente de `data_pedido` quando fizer sentido, sem perder a data original, e cobrir pedidos antigos, novos e parcialmente recebidos.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ relatorios_operacionais.py
-    where = ["data_pedido BETWEEN ? AND ?"]
+    where = ["COALESCE(data_pedido, data_geracao, criado_em)::date BETWEEN ? AND ?"]
```

