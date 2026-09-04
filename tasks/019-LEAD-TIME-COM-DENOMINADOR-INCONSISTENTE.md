# PROBLEM

- **Severidade:** média
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/services/relatorios.py:145-165`

## Explicação para leigos

Pedidos antigos sem a data formal do pedido agora aparecem no relatório de compras, mas podem reduzir artificialmente o prazo médio do fornecedor.

## Evidência e análise técnica

O filtro foi corrigido para usar `COALESCE(data_pedido, data_geracao, criado_em)`. Porém, o numerador do lead time continua subtraindo apenas `data_pedido`, enquanto o denominador conta todo pedido recebido que possua `data_recebida`.

Para um pedido recebido com `data_pedido IS NULL`, o `SUM` ignora a diferença nula, mas o `COUNT` inclui a linha. Assim, o total de dias é dividido por mais pedidos do que aqueles que contribuíram para a soma.

## Impacto

O prazo médio fica menor que o real e pode influenciar avaliação de fornecedores, estoque de segurança e cálculo de reposição.

## Solução proposta

Usar a mesma data efetiva no numerador, filtro e denominador. Se nenhuma das datas de origem existir, excluir a linha do cálculo e informar a quantidade de registros incompletos no relatório.

Adicionar teste com mistura de pedidos modernos e legados. Nenhum teste foi executado nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/services/relatorios.py b/backend/catalog_server/services/relatorios.py
@@
- SUM(CASE WHEN status='recebido' THEN (data_recebida::date - data_pedido::date) END) /
- NULLIF(COUNT(*) FILTER (WHERE status='recebido' AND data_recebida IS NOT NULL),0)
+ SUM(CASE WHEN status='recebido' AND data_recebida IS NOT NULL
+          THEN data_recebida::date
+             - COALESCE(data_pedido, data_geracao, criado_em::timestamptz)::date END) /
+ NULLIF(COUNT(*) FILTER (WHERE status='recebido' AND data_recebida IS NOT NULL
+                         AND COALESCE(data_pedido, data_geracao, criado_em::timestamptz) IS NOT NULL),0)
```
