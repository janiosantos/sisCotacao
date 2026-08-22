# Regra de Emissão Fiscal

O documento fiscal deve conservar um snapshot dos dados do produto, tributos, preços, quantidades, códigos e valores aplicados no momento da operação. A regra fiscal vigente hoje não pode reescrever uma nota autorizada ontem.

Separar estados `RASCUNHO`, `VALIDADO`, `PENDENTE`, `ENVIADO`, `AUTORIZADO`, `REJEITADO`, `CANCELADO`, `INUTILIZADO` e `CONTINGENCIA`. Cada transição deve ser autorizada, auditada e idempotente.

Integrações externas devem usar correlation/idempotency key, guardar protocolo, resposta, XML, eventos e mensagens de rejeição. Certificados e segredos nunca devem aparecer em logs.
