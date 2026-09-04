# PROBLEM

- **Severidade:** alta
- **Categoria:** segurança
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/blueprints/pages.py:43-53`; `backend/catalog_server/blueprints/api_usuarios.py:17-24, 207-259`; `backend/catalog_server/permissao.py:46-113, 147-154`

## Explicação para leigos

Desativar um funcionário bloqueia as APIs, mas não necessariamente bloqueia as páginas de impressão recém-protegidas. Se o navegador ainda tiver a sessão antiga, um usuário comum desativado pode continuar consultando pedidos, boletos e etiquetas.

## Evidência e análise técnica

As páginas fora de `/api` usam `usuario_id_requisicao()`, que aceita o ID guardado na sessão. `_autorizar_impressao()` chama `tem_permissao()` sem revalidar status ou versão do token.

Em `_carregar`, somente a consulta que detecta o perfil Administrador faz `JOIN usuarios` e exige `u.ativo=1`. As consultas de permissões dos demais perfis e overrides não verificam a tabela `usuarios`. Após invalidar o cache, um usuário comum inativo volta a receber as mesmas permissões pela sessão. O gate Bearer possui validação correta, mas não é executado nessas páginas.

## Impacto

Ex-funcionários ou contas suspensas podem acessar documentos comerciais e financeiros enquanto o cookie estiver válido. O risco inclui IDOR por troca do ID da URL dentro do conjunto de documentos imprimíveis.

## Solução proposta

Criar uma função única de autenticação para páginas que valide usuário ativo e `token_version`, ou emitir um cookie de sessão versionado. Como defesa adicional, `_carregar` deve verificar `usuarios.ativo=1` antes de compor qualquer perfil ou override.

Testar login, desativação e acesso com o mesmo cookie para administrador e usuário comum; ambos devem receber `401` ou `403`. Nenhum teste foi executado agora.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/backend/catalog_server/permissao.py b/backend/catalog_server/permissao.py
@@
     with system_conn() as conn:
+        ativo = conn.execute(
+            "SELECT 1 FROM usuarios WHERE id=? AND ativo=1", (usuario_id,)
+        ).fetchone()
+        if not ativo:
+            return {}
         # Perfil Administrador => superuser.
diff --git a/backend/catalog_server/blueprints/pages.py b/backend/catalog_server/blueprints/pages.py
@@
-    actor = usuario_id_requisicao()
+    actor = usuario_ativo_da_sessao()
```
