# Configurações, atualizações e integrações

## Configurações (`#/configuracoes`)

**O que é?** Parâmetros de loja, impressora, integrações, flags e gatilhos
contábeis. **Para que serve?** Adequar o ERP à operação. **Papel:** altera
comportamento transversal, por isso requer teste e rollback.

Leia o impacto, altere somente o necessário, salve, valide em ambiente seguro e
registre a decisão. Nunca cole senha, certificado, token ou chave na tela.

## Atualizações (`#/atualizacoes`)

**O que é?** Notas das versões. **Para que serve?** Orientar treinamento e
validação pós-release. **Papel:** informa mudanças, mas não substitui o fluxo de
publicação autorizado.

## Webhooks (`#/webhooks`)

**O que é?** Monitoramento de eventos externos. **Para que serve?** Investigar
retornos de PIX/boleto e retries. **Papel:** conectar provedor e financeiro com
idempotência. Não marque pagamento manualmente sem validar evento e título.

## Outras telas de apoio

`#/fiscal`, `#/bancos`, `#/diagnostico-variacoes`, `#/solicitacoes` e as abas de
Compras/Estoque seguem as páginas específicas desta wiki.

## Auditoria

Toda alteração de configuração e reprocessamento de integração deve ter
responsável, data, versão e resultado.

## Capturas

- [Configurações](capturas/configuracoes-desktop-dev.png), [Usuários](capturas/usuarios-desktop-dev.png), [Perfis](capturas/perfis-desktop-dev.png), [Atualizações](capturas/atualizacoes-desktop-dev.png) e [Webhooks](capturas/webhooks-desktop-dev.png).
