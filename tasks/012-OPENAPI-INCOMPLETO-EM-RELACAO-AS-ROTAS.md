# PROBLEM
- **Severidade:** média
- **Categoria:** incoerência
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/openapi.json:1-...`, `backend/catalog_server/blueprints/*.py`

## Explicação para leigos
O arquivo OpenAPI é apresentado como contrato da API, mas documenta apenas uma parte das rotas realmente registradas. Assim, frontend, integrações, QA e operadores não conseguem confiar nele para saber quais endpoints existem ou quais permissões e payloads esperar.

## Evidência e análise técnica
Uma leitura estática dos decorators em `backend/catalog_server/blueprints` encontrou centenas de caminhos normalizados, enquanto `backend/openapi.json` contém um subconjunto muito menor. Entre os caminhos não encontrados estão operações de crédito, recebimento de compras, anexos financeiros, recebimentos de caixa, emissão fiscal, parceiros, inventário, reposição, novos relatórios de clientes e vários endpoints de produtos. O próprio documento informa “fase 1”, embora o projeto já tenha regras de contrato por blueprint tocado.

## Impacto
Clientes podem implementar uma URL com payload incorreto, usar uma ação RBAC errada ou depender de endpoint não documentado. A ausência de schemas também aumenta regressões entre backend e frontend e dificulta a geração de testes de contrato.

## Solução proposta
Gerar ou validar o documento a partir do mapa de rotas em CI, normalizando parâmetros Flask para `{param}`. Para cada endpoint, declarar método, autenticação, recurso/ação RBAC, parâmetros, request body, respostas de sucesso/erro e exemplos sem dados sensíveis. Bloquear a pipeline quando uma rota pública/importante ficar sem contrato, mantendo versionamento da API e changelog de mudanças incompatíveis.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ CI
+python scripts/check_openapi_coverage.py \
+  --routes backend/catalog_server/blueprints \
+  --spec backend/openapi.json \
+  --require-auth-and-error-schemas
```

