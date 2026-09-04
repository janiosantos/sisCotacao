# PROBLEM
- **Severidade:** crítica
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/blueprints/api_orcamentos.py:356-378, 794-813`; `backend/catalog_server/repositories/estoque.py:62-134`; `backend/catalog_server/services/relatorios_operacionais.py:113-181`

## Explicação para leigos
Quando o sistema permite vender mesmo sem estoque suficiente, a baixa usa um caminho antigo de movimentação. A devolução também usa esse caminho antigo e, se algo der errado, o erro é ignorado: o sistema pode informar que a venda foi devolvida mesmo sem recolocar o produto no estoque.

Isso também prejudica os relatórios, porque a movimentação antiga não carrega a origem da venda nem o custo necessário para calcular corretamente o CMV e a margem.

## Evidência e análise técnica
Na finalização do orçamento, `api_orcamentos.py` chama `movimentar_fato()` somente quando `bloquear_sem_estoque()` está ativo. No ramo legado, chama `estoque_repo.movimentar()` sem `origem_tipo`, `origem_id`, `idempotency_key` e snapshot de custo.

O relatório analítico de vendas agrega o custo em `estoque_movimento` filtrando `tipo='saida' AND origem_tipo='venda'`. Portanto, as vendas finalizadas pelo ramo legado não são encontradas pelo CTE `custo`, gerando CMV zerado ou subestimado e margem artificialmente maior.

No endpoint de devolução, cada entrada é feita por `movimentar()` e qualquer exceção é capturada por `except Exception: pass`. Depois disso, contas são canceladas e o orçamento é marcado como devolvido mesmo que nenhuma, ou apenas parte, das entradas de estoque tenha sido realizada. A operação também não usa uma chave idempotente nem uma transação única equivalente ao faturamento.

## Impacto
- Saldos de estoque podem ficar divergentes após devoluções parciais ou falhas de banco.
- O usuário pode receber confirmação de devolução sem que o estoque tenha sido recomposto.
- CMV, margem, curva de rentabilidade e decisões de compra podem ficar incorretos nas vendas feitas com estoque negativo permitido.
- Reprocessamentos podem duplicar entradas de devolução, pois não há idempotência específica.
- A falha silenciosa dificulta auditoria, conciliação e suporte operacional.

## Solução proposta
Usar o livro de fatos (`movimentar_fato`) para toda saída e entrada de estoque, independentemente da configuração de bloqueio. Preservar a configuração apenas como regra de validação de saldo, nunca como escolha do modelo de registro.

Na venda, informar sempre `origem_tipo='venda'`, `origem_id`, documento, custo unitário/snapshot aplicável e uma `idempotency_key` determinística por item. Na devolução, criar fatos de entrada vinculados à venda e à devolução, com uma chave única por item; calcular somente a quantidade ainda não devolvida.

Executar a devolução em transação única, com bloqueio das linhas relevantes. Se qualquer item falhar, fazer rollback e retornar erro operacional (por exemplo, `409`), sem cancelar contas ou alterar o status da venda. Remover o `except Exception: pass` e registrar falhas com contexto. Para dados históricos, criar uma rotina explícita de reconciliação que identifique movimentos legados sem origem e não invente custos sem evidência.

## Diff/patch proposto - NÃO APLICADO
```diff
diff --git a/backend/catalog_server/blueprints/api_orcamentos.py b/backend/catalog_server/blueprints/api_orcamentos.py
@@
-                    else:
-                        estoque_repo.movimentar(...)
+                    else:
+                        estoque_repo.movimentar_fato(
+                            deposito_id=..., produto_id=vid, tipo="saida",
+                            quantidade=qtd,
+                            idempotency_key=f"venda:{orcamento_id}:item:{item_id}",
+                            origem_tipo="venda", origem_id=orcamento_id,
+                            documento=orc.get("numero", ""), _conn=conn,
+                        )
@@
-        try:
-            estoque_repo.movimentar(...)
-            devolvidos += 1
-        except Exception:
-            pass
+        estoque_repo.movimentar_fato(
+            deposito_id=..., produto_id=vid, tipo="entrada", quantidade=qtd,
+            idempotency_key=f"devolucao:{orcamento_id}:item:{item_id}",
+            origem_tipo="devolucao", origem_id=orcamento_id,
+            documento=f"DEV {orc.get('numero', '')}", _conn=conn,
+        )
+        devolvidos += 1
```
