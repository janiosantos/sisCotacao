# PROBLEM

- **Severidade:** alta
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `deployment/compose/docker-compose.staging.yml:38-47`; `.github/workflows/deploy-staging.yml:70-86`; `backend/catalog_server/app_factory.py:345-370`; `backend/catalog_server/blueprints/api_usuarios.py:263-266`

## Explicação para leigos

Em um staging novo, o sistema cria sozinho um administrador com uma senha aleatória que ninguém conhece. Como já passa a existir um usuário, a tela de primeiro acesso também deixa de permitir a criação do administrador correto.

## Evidência e análise técnica

O compose agora define `CATALOG_ENV=staging`. A fábrica exclui apenas o valor exato `production` do bootstrap: `config.ENVIRONMENT != "production"`. Com banco vazio, gera `secrets.token_urlsafe(32)`, cria `admin` e não registra a senha. O compose e o workflow não fornecem `CATALOG_BOOTSTRAP_ADMIN_PASSWORD`.

Depois dessa inserção, `/api/primeiro-usuario` responde que o banco não está vazio. O smoke usa credenciais próprias e falhará se elas não coincidirem com esse usuário aleatório. A situação pode ficar mascarada em um volume antigo de staging.

## Impacto

O primeiro deploy em staging limpo pode ficar sem acesso administrativo e falhar no smoke. Recriar o banco repete o problema, exigindo intervenção manual incompatível com um ambiente reproduzível.

## Solução proposta

Permitir bootstrap automático somente em `development` e `test`, mediante flag explícita. Para staging, criar o usuário por etapa idempotente e auditável do pipeline usando segredo dedicado, ou preservar o fluxo de primeiro acesso sem criar usuário oculto.

Validar posteriormente os cenários banco vazio e banco existente, sem imprimir a senha nos logs. Nenhum workflow ou teste foi executado nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/app_factory.py b/backend/catalog_server/app_factory.py
@@
-        if config.ENVIRONMENT != "production" and usuario_repo.count() == 0:
+        bootstrap_habilitado = os.getenv("ALLOW_BOOTSTRAP_ADMIN", "0") == "1"
+        if config.ENVIRONMENT in {"development", "test"} and bootstrap_habilitado \
+                and usuario_repo.count() == 0:
             ...
```
