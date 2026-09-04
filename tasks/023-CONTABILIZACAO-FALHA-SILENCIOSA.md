# PROBLEM

- **Severidade:** alta
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/blueprints/api_compras.py:127-150`; `backend/catalog_server/blueprints/api_estoque.py:323-345, 672-699`; `backend/catalog_server/contabil_gatilhos.py:74-123`

## Explicação para leigos

Uma compra ou ajuste de estoque pode ser concluído mesmo quando a contabilização configurada falha. O erro é descartado e ninguém recebe aviso, deixando o operacional diferente da contabilidade.

## Evidência e análise técnica

Após gerar pedidos, `api_compras.py` dispara lançamentos em transações separadas dentro de `try/except Exception: pass`. Os dois caminhos de ajuste/inventário em `api_estoque.py` repetem o padrão. Não há log, evento pendente ou retorno que sinalize a falha.

`contabil_gatilhos.disparar()` já aceita `_conn`, mas esses chamadores não compartilham a conexão do evento de negócio. A idempotência evita duplicidade em retry, porém não existe retry automático quando a exceção é silenciada.

## Impacto

Pedidos, estoque, DRE, razão e saldos contábeis podem divergir. A falha só tende a aparecer na conciliação manual, sem evidência suficiente para saber quais eventos precisam ser repostados.

## Solução proposta

Quando o gatilho estiver ativo e for parte obrigatória da operação, gravar evento e lançamento na mesma transação. Se a contabilização for eventual, gravar uma outbox transacional obrigatória e processá-la com retry/dead-letter. Ausência de configuração pode continuar retornando `False`; exceção técnica não pode ser tratada como gatilho inativo.

Adicionar testes que forcem falha contábil em compra, ajuste e inventário, verificando rollback ou outbox pendente e auditoria. Nenhum teste foi executado agora.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/blueprints/api_compras.py b/backend/catalog_server/blueprints/api_compras.py
@@
-    pedidos = compras_repo.gerar_pedidos(cotacao_id, logica)
-    try:
+    with system_conn() as conn:
+        pedidos = compras_repo.gerar_pedidos(cotacao_id, logica, _conn=conn)
         for ped in pedidos or []:
             contabil_gatilhos.disparar(
                 "compra", evento_id=int(ped["id"]), ...,
+                _conn=conn,
             )
-    except Exception:
-        pass
```
