---
name: fiscal-emission
description: Implementar ciclo de vida, validação, transmissão, autorização, rejeição, cancelamento e contingência de NF-e/NFC-e, preservando snapshots e auditoria. Usar em emissão ou integração fiscal.
---

# Fiscal Emission

Separar documento comercial interno, documento fiscal e protocolo externo. Validar cadastro, regras fiscais, numeração, ambiente, certificado e consistência antes do envio.

Persistir tentativas, respostas, XML, protocolo, eventos e status. Tornar envio e consulta idempotentes. Nunca marcar como autorizado sem confirmação válida do serviço externo.
