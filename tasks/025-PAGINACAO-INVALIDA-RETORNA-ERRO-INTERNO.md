# PROBLEM

- **Severidade:** média
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/blueprints/api_clientes.py:51-62`; `backend/catalog_server/blueprints/api_suppliers.py:20-34`

## Explicação para leigos

Os novos endereços paginados quebram com erro interno se alguém enviar letras ou um número malformado nos campos de página. Isso deveria ser tratado como entrada inválida, sem parecer uma falha do servidor.

## Evidência e análise técnica

Os dois endpoints chamam `int(request.args.get(...))` diretamente para `limit` e `offset`, fora de qualquer validação. Valores como `?limit=abc` ou `?offset=1.5` levantam `ValueError`, que não é convertido para resposta de domínio e chega ao handler genérico como erro 500.

Outros blueprints já usam o conversor do Werkzeug (`request.args.get(..., type=int)`), demonstrando um padrão interno disponível.

## Impacto

Links malformados, estado antigo do frontend ou chamadas externas podem gerar 500, poluir monitoramento e degradar a experiência de listagem. Um cliente pode repetir a chamada e ampliar carga desnecessariamente.

## Solução proposta

Centralizar leitura de paginação em helper que diferencie ausência de valor de valor inválido, aplique limites e retorne `400` com contrato estável. Usar o helper em clientes e fornecedores e documentar os parâmetros no OpenAPI.

Adicionar testes para ausente, zero, negativo, acima do máximo e texto inválido. Nenhum teste foi executado nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/blueprints/api_clientes.py b/backend/catalog_server/blueprints/api_clientes.py
@@
-    limit = min(max(int(request.args.get("limit", 50) or 50), 1), 200)
-    offset = max(int(request.args.get("offset", 0) or 0), 0)
+    try:
+        limit, offset = ler_paginacao(request.args, default=50, maximo=200)
+    except ValueError as exc:
+        return jsonify({"error": str(exc), "code": "paginacao_invalida"}), 400
```
