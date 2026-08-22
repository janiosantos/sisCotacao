# Regra de API

As APIs devem receber contexto fiscal explícito e responder com resultado, origem da regra, versão, avisos e erros acionáveis. Não expor segredos, certificados, tokens ou dados desnecessários.

Validar códigos, UFs, datas, decimais, enumerações e permissões no servidor. Operações de resolução e cálculo devem ser idempotentes quando aplicável. Alterações de TaxRule devem exigir autorização adequada e produzir auditoria.

Diferenciar erro de validação, ausência de parametrização, conflito de regras, falha de integração externa e erro interno. Não mascarar ausência de regra como alíquota zero.
