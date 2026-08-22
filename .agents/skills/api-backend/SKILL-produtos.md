---
name: api-backend
description: Construir APIs backend seguras e auditáveis para cadastro, regras fiscais, resolução, cálculo e emissão. Usar em endpoints, contratos, validações e integrações.
---

# API Backend

Definir contrato antes da implementação. Validar autorização por operação, entrada e vigência no servidor. Usar respostas estruturadas com `status`, `rule_id`, `rule_version`, `warnings` e `calculated_values`.

Cobrir idempotência, concorrência, paginação, observabilidade, limites, erros e compatibilidade. Nunca aceitar do cliente valores calculados como fonte de verdade sem recalcular ou verificar no servidor.
