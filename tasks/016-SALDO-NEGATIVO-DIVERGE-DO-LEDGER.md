# PROBLEM

- **Severidade:** crítica
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/blueprints/api_orcamentos.py:350-372`; `backend/catalog_server/repositories/estoque.py:295-338, 605-630`; `deployment/scripts/check-reconciliacao.sh:6-16`

## Explicação para leigos

Quando a loja permite vender um produto sem saldo suficiente, o histórico registra a quantidade total vendida, mas o saldo mostrado é travado em zero. Os dois controles passam a contar histórias diferentes sobre o mesmo estoque.

## Evidência e análise técnica

A finalização envia `permitir_saldo_negativo=True` quando o bloqueio está desligado. Em `movimentar_fato`, a validação é corretamente ignorada, porém o novo saldo é calculado por `max(0, saldo_atual - q)`. O fato gravado mantém `quantidade=q`, enquanto `saldo_posterior` e `estoque_saldo.quantidade` ficam em zero.

A reconciliação deriva o saldo somando entradas e subtraindo saídas. Exemplo: saldo 2 e venda 5 produzem ledger `-3` e saldo materializado `0`. O gate de staging falha por definição, e uma entrada posterior de 3 unidades resultará em materializado `3`, embora o ledger reconciliado seja zero.

## Impacto

O saldo disponível, necessidade de compra, ruptura, inventário e valor de estoque ficam incorretos após qualquer venda acima do saldo. Staging também pode ser bloqueado pelo próprio gate de reconciliação.

## Solução proposta

Se a política realmente permite estoque negativo, persistir `saldo_atual - q` sem truncar. Se o negócio quiser exibir zero, manter o saldo contábil negativo como fonte de verdade e calcular uma apresentação separada, nunca alterar o ledger. A alternativa é registrar somente a quantidade efetivamente atendida e criar um backorder para o restante, mas isso muda o fluxo comercial e exige decisão explícita.

Adicionar testes para saldo 2/venda 5, entrada posterior, retry idempotente e reconciliação sem divergência. Nenhum teste foi executado nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/repositories/estoque.py b/backend/catalog_server/repositories/estoque.py
@@
-                    novo_saldo = max(0, saldo_atual - q)
+                    novo_saldo = saldo_atual - q
@@
-                    novo_saldo = max(0, saldo_atual - q)
+                    novo_saldo = saldo_atual - q
```
