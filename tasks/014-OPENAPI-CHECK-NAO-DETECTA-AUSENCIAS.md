# PROBLEM

- **Severidade:** alta
- **Categoria:** bug
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `scripts/check_openapi_coverage.py:51-75`

## Explicação para leigos

O novo verificador criado para avisar quando uma API não está documentada tende a afirmar que está tudo correto mesmo quando faltam rotas. Isso transforma um controle de qualidade em uma falsa sensação de segurança.

## Evidência e análise técnica

O Flask adiciona automaticamente `HEAD` e `OPTIONS` às rotas `GET`. O filtro de faltantes exige que o caminho não tenha nenhum desses métodos: `not any(m in ("OPTIONS", "HEAD") for m in metodos)`. Como quase toda regra registrada contém pelo menos `OPTIONS`, a condição fica falsa e a rota ausente deixa de entrar em `faltando`.

Além disso, a cobertura é comparada apenas pelo caminho. Um caminho existente no OpenAPI, mas com `POST`, `PUT` ou `DELETE` ausente, é contado como totalmente coberto.

## Impacto

O modo `--strict` pode retornar sucesso com endpoints e operações sem contrato. Mudanças incompatíveis podem chegar ao frontend, staging ou produção sem que o gate detecte a diferença.

## Solução proposta

Remover `HEAD` e `OPTIONS` do conjunto e comparar pares `(caminho, método)` entre o `url_map` e cada operação declarada no OpenAPI. A lista de exceções deve identificar também os métodos permitidos, para não ocultar operações novas no mesmo caminho.

Depois da correção, validar com testes unitários que criem uma rota `GET` e outra `POST` ausentes, uma rota parcialmente documentada e uma exceção explícita. Esses testes devem ser executados posteriormente; não foram executados nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/scripts/check_openapi_coverage.py b/scripts/check_openapi_coverage.py
@@
-    faltando = sorted(
-        p for p, metodos in rota_metodos.items()
-        if p not in spec_paths and not any(m in ("OPTIONS", "HEAD") for m in metodos)
-    )
+    operacoes_spec = {
+        (path, method.upper())
+        for path, item in spec.get("paths", {}).items()
+        for method in item
+        if method.lower() in {"get", "post", "put", "patch", "delete"}
+    }
+    operacoes_app = {
+        (path, method)
+        for path, metodos in rota_metodos.items()
+        for method in metodos - {"HEAD", "OPTIONS"}
+    }
+    faltando = sorted(operacoes_app - operacoes_spec)
```
