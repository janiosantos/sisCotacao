# Workflow: NFC-e em Contingência Offline

1. Detectar indisponibilidade com limite e política documentados.
2. Verificar pré-requisitos locais para contingência e numeração.
3. Emitir documento em estado `CONTINGENCIA`, preservar horário, motivo e snapshot.
4. Imprimir o documento auxiliar conforme configuração homologada.
5. Enfileirar transmissão posterior com idempotency key.
6. Ao restabelecer conexão, transmitir e reconciliar autorização/rejeição.
7. Tratar o prazo e demais requisitos legais como configuração dependente de validação atualizada; não assumir prazo fixo sem revisão fiscal.
