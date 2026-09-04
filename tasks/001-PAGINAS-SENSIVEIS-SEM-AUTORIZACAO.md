# PROBLEM
- **Severidade:** alta
- **Categoria:** segurança
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/app_factory.py:419-485`, `backend/catalog_server/blueprints/pages.py:43-130`

## Explicação para leigos
O sistema exige login para a API, mas não exige login para várias páginas HTML que mostram orçamentos, pedidos de compra, boletos e etiquetas. Qualquer pessoa que descubra ou adivinhe um identificador pode abrir esses documentos diretamente. O mesmo vale para arquivos servidos por `/images`.

## Evidência e análise técnica
`exigir_token()` retorna imediatamente para qualquer caminho que não comece por `/api/`. As rotas `/etiquetas/imprimir`, `/orcamentos/<id>/imprimir`, `/orcamentos/venda/<id>/imprimir`, `/orcamentos/<id>/boleto` e `/compras/pedidos/<id>/imprimir` são registradas em `pages.py`, consultam o banco e renderizam dados sem chamar `usuario_id_requisicao()` ou `permissao.tem_permissao()`. A própria função `_autorizar_pagina_relatorio()` existe para relatórios, mas não é usada nessas páginas. Em `app_factory.py`, `/images/<path:name>` também retorna o arquivo diretamente.

## Impacto
Há exposição de nomes, documentos, valores, condições de pagamento, dados de clientes, fornecedores e boletos. Além da confidencialidade, a ausência de autorização cria IDOR: trocar o número na URL pode acessar o documento de outra operação. O vazamento de imagens/anexos aumenta o risco de exposição de comprovantes.

## Solução proposta
Criar um middleware de autenticação para páginas internas e separar explicitamente as exceções públicas: portal do fornecedor por token e imagens públicas do catálogo institucional. As páginas de impressão devem validar sessão/token, recurso e ação `imprimir`, além de verificar se o documento pode ser visto pelo perfil. Servir imagens privadas por endpoint autorizado ou URL assinada com expiração; nunca expor o diretório bruto de comprovantes. Adicionar testes de acesso anônimo, acesso cruzado por ID e permissão de impressão.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ app_factory.py
+@app.before_request
+def exigir_auth_paginas_internas():
+    if request.path.startswith(("/api/", "/fornecedor/", "/api/publico/")):
+        return
+    if request.path.startswith(("/etiquetas/", "/orcamentos/", "/compras/pedidos/")):
+        exigir_sessao_e_permissao("imprimir")
```

