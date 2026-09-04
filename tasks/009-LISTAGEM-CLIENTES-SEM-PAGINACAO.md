# PROBLEM
- **Severidade:** média
- **Categoria:** ponto fraco
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/blueprints/api_clientes.py:43-47`, `backend/catalog_server/repositories/clientes.py:8-24`, `backend/catalog_server/repositories/suppliers.py:18-46`

## Explicação para leigos
As telas de cadastro carregam todos os clientes e fornecedores em uma única resposta. Em uma grande loja, isso cresce indefinidamente e deixa a tela lenta, consome memória e pode travar o navegador.

## Evidência e análise técnica
`GET /api/clientes` chama `cliente_repo.list()` sem `limit`, `offset`, busca ou cursor. O repositório executa `SELECT c.* ... ORDER BY c.nome` e retorna todo o resultado. O repositório de fornecedores repete o padrão com `SELECT * FROM fornecedores` sem paginação. A busca rápida de clientes possui limite, mas a listagem principal não.

## Impacto
Tempo de resposta e payload aumentam com a base. O frontend precisa renderizar mais registros, prejudicando filtros, navegação por teclado e dispositivos mais modestos. A consulta também pode pressionar conexões e memória do backend.

## Solução proposta
Adotar contrato paginado comum com `q`, `limit` limitado, `cursor`/`offset`, total opcional e ordenação whitelist. Usar busca server-side para comboboxes e virtualização somente quando necessário. Manter endpoints de contexto pequenos, retornando apenas campos usados na tela, e instrumentar tempo/quantidade de linhas.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ api_clientes.py
-    return jsonify(cliente_repo.list(somente_ativos=somente_ativos, vendedor_id=vendedor_id))
+    return jsonify(cliente_repo.list_page(
+        somente_ativos=somente_ativos, vendedor_id=vendedor_id,
+        q=request.args.get("q"), limit=request.args.get("limit", 50, type=int),
+        cursor=request.args.get("cursor"),
+    ))
```

