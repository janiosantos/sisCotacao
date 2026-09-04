# PROBLEM
- **Severidade:** alta
- **Categoria:** segurança
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `deployment/compose/docker-compose.staging.yml:38-44`, `backend/catalog_server/config.py:24-32`, `backend/catalog_server/app_factory.py:439-441`, `backend/catalog_server/payments/base.py:48-65`, `backend/catalog_server/payments/asaas.py:33-42`, `backend/catalog_server/payments/mercadopago.py:31-42`

## Explicação para leigos
O staging é acessível externamente por HTTPS, mas o compose não define uma chave secreta própria. Com isso, o sistema usa a chave pública de desenvolvimento (`catalog-server-local-dev`) para assinar tokens e aceita webhooks sem assinatura quando o segredo do provedor não está preenchido.

## Evidência e análise técnica
O compose de staging não define `CATALOG_ENV`, `CATALOG_SECRET` nem `PAYMENT_WEBHOOK_SECRET`. `config.py` assume `CATALOG_ENV=development` e usa `catalog-server-local-dev` quando `CATALOG_SECRET` está ausente. A proteção contra a chave padrão só é executada quando o ambiente é exatamente `production`. As validações de webhook retornam sem erro quando não há segredo e o ambiente não é produção. A rota de webhook é deliberadamente liberada no gate central.

## Impacto
Como staging usa o mesmo domínio/certificado e uma porta pública, um token forjado com a chave conhecida pode acessar o staging com qualquer identidade compatível com o banco. Um webhook falso pode localizar um `payment_id` conhecido e marcar uma conta como paga, movimentando o caixa do staging. O risco aumenta se alguma credencial, banco ou integração for compartilhada por engano.

## Solução proposta
Definir `CATALOG_ENV=staging` e exigir `CATALOG_SECRET` forte, exclusivo e injetado por secret manager no backend e workers. Fazer o bootstrap falhar se qualquer ambiente exposto não tiver segredo. Exigir segredo/assinatura também em staging e sandbox; para testes, usar um segredo explícito e fixtures assinadas. Validar que cada provedor tenha webhook configurado antes de habilitar a URL pública e registrar tentativa sem assinatura.

## Diff/patch proposto - NÃO APLICADO
```diff
@@ deployment/compose/docker-compose.staging.yml
+      - CATALOG_ENV=staging
+      - CATALOG_SECRET=${CATALOG_STAGING_SECRET:?CATALOG_STAGING_SECRET obrigatório}
+      - PAYMENT_WEBHOOK_SECRET=${PAYMENT_STAGING_WEBHOOK_SECRET:?PAYMENT_STAGING_WEBHOOK_SECRET obrigatório}
@@ payments/base.py
-            return  # dev/sandbox sem segredo: aceita
+            raise WebhookNaoAutorizado("Webhook sem segredo configurado")
```

