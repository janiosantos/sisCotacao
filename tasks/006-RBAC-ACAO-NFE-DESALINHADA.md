# PROBLEM
- **Severidade:** média
- **Categoria:** incoerência
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `backend/catalog_server/app_factory.py:77-83`, `backend/catalog_server/app_factory.py:196-238`, `backend/catalog_server/blueprints/api_fiscal_avancado.py:12-14`

## Explicação para leigos
A rota de emissão de NF-e declara que exige a permissão `fiscal.emitir`, mas o gate central pode barrá-la antes exigindo `fiscal.cadastrar`, porque a URL começa por `/api/nfe` e o método é `POST`.

## Evidência e análise técnica
`_recurso_da_rota()` mapeia `/api/nfe` para `fiscal`. `_acao_da_rota()` trata como `emitir` somente URLs de `/api/orcamentos/<id>/nfce`, `/nfe` ou `/focus/...`. A rota independente `/api/nfe/emitir/<id>` não entra nessa regra e cai no mapa HTTP `POST -> cadastrar`. Depois disso, o decorator da própria função exige `fiscal.emitir`, mas ele nunca é alcançado quando o usuário tem apenas a permissão específica de emissão.

## Impacto
Perfis fiscais corretamente configurados para emitir podem receber 403 inesperado, enquanto o comportamento depende de uma permissão administrativa adicional que não representa a operação. Isso quebra segregação de funções e dificulta auditoria de autorização.

## Solução proposta
Mapear explicitamente toda rota de emissão para `emitir` no gate central e manter o decorator como defesa em profundidade. Criar uma tabela declarativa de operações fiscais, revisar as rotas de entrada/saída e testar combinações de perfil com `emitir`, `cadastrar`, `configurar` e `visualizar`.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ app_factory.py
+    if method == "POST" and path.startswith("/api/nfe/emitir/"):
+        return "emitir"
```

