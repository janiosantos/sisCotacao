# PROBLEM

- **Severidade:** alta
- **Categoria:** ponto fraco
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `scripts/check_openapi_coverage.py:46-59`; `backend/catalog_server/app_factory.py:345-380, 530`; `backend/catalog_server/db.py:32-66`

## Explicação para leigos

Um comando que deveria apenas conferir documentação inicializa a aplicação real. Dependendo das variáveis do ambiente, essa simples conferência pode aplicar migrações, criar cadastros iniciais e iniciar o processo de impressão.

## Evidência e análise técnica

O script importa e chama `create_app()` para obter o mapa de rotas. A fábrica consulta repositórios durante o bootstrap; o primeiro `system_conn()` chama `_ensure_migrations()` e, com `AUTO_MIGRATE=1`, aplica migrações. A mesma fábrica pode criar o administrador e o consumidor padrão e chama `impressao_service.start_worker()`.

Portanto, o verificador não é somente leitura e não pode ser usado com segurança como lint local ou gate genérico de CI. O seu docstring informa apenas que banco e segredo são necessários, sem declarar esses efeitos.

## Impacto

Uma verificação de contrato pode alterar um banco apontado por engano, consumir ou processar fila de impressão e produzir resultados diferentes conforme o estado externo. Também fica lenta e frágil quando PostgreSQL está indisponível.

## Solução proposta

Separar o registro de blueprints dos bootstraps operacionais. A fábrica deve aceitar um modo explícito de inspeção que registre rotas sem migração, seed, conexão de banco ou workers. Melhor ainda, manter o catálogo de contratos/rotas como dado estático reutilizado pela aplicação e pelo verificador.

Criar teste que execute a coleta de rotas com uma URL de banco deliberadamente inválida e confirme que nenhuma conexão ou chamada de worker ocorre. O teste é recomendação posterior e não foi executado agora.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/app_factory.py b/backend/catalog_server/app_factory.py
@@
-def create_app() -> Flask:
+def create_app(*, bootstrap: bool = True, start_workers: bool = True) -> Flask:
@@
-    try:
+    if bootstrap:
+        try:
             ...
@@
-    impressao_service.start_worker()
+    if start_workers:
+        impressao_service.start_worker()
diff --git a/scripts/check_openapi_coverage.py b/scripts/check_openapi_coverage.py
@@
-    app = create_app()
+    app = create_app(bootstrap=False, start_workers=False)
```
