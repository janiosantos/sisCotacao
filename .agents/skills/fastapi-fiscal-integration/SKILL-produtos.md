---
name: fastapi-fiscal-integration
description: Integrar FastAPI com provedores externos de emissão fiscal, como APIs SaaS, mantendo separação entre venda, motor fiscal, outbox, tentativas, consulta, XML, protocolo e estados.
---

# FastAPI e API Fiscal

Criar endpoints internos para preparar, validar, enviar, consultar e processar eventos. Encapsular o provedor atrás de uma porta/adaptador para evitar dependência do domínio.

Usar chave de referência/idempotência por documento, timeout, retry com backoff, circuit breaker, logs sem segredos e reconciliação por consulta. Persistir request sanitizado, resposta, status, protocolo, XML e PDF conforme política de segurança e retenção.

Nunca marcar documento como autorizado somente porque a requisição HTTP foi aceita. A autorização deve ser confirmada pelo retorno do provedor/SEFAZ e validada contra a chave e o ambiente corretos.
