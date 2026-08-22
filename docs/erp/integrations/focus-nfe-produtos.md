# Integração com API Fiscal SaaS

O material recebido sugere usar um provedor SaaS, como Focus NFe, para reduzir a implementação direta de XML, assinatura digital e comunicação com SEFAZ. A documentação pública consultada descreve envio estruturado, autenticação, referências de emissão, endpoints separados para emissão/consulta de NF-e e NFC-e e retornos com status, XML e documentos relacionados [1].

## Arquitetura recomendada

O FastAPI deve montar um payload a partir do pedido, do snapshot fiscal e das configurações da empresa. O adaptador do provedor deve traduzir o contrato interno para o contrato externo. O domínio não deve conhecer detalhes SOAP, URLs, tokens ou campos específicos do fornecedor.

Persistir `provider`, `environment`, `reference`, `request_hash`, `attempt`, `http_status`, `provider_status`, `access_key`, `protocol`, `xml`, `pdf`, `error_code`, `error_message`, `created_at` e `updated_at`. Mascarar tokens e dados sensíveis.

Usar consulta após timeout ou resposta ambígua antes de tentar novo envio. Confirmar no contrato vigente do provedor a semântica de referência, callbacks/webhooks, idempotência, prazos, contingência, limites e retenção.

## Referência

[1]: https://doc.focusnfe.com.br/reference/introducao — Documentação API Focus NFe: introdução, autenticação, envio, consulta e retorno.
