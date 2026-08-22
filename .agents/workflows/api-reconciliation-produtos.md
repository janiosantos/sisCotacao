# Workflow: Reconciliação com API Fiscal

1. Ler documentos pendentes, com lock/claim idempotente.
2. Consultar status quando houve timeout ou resposta ambígua antes de reenviar.
3. Comparar referência, chave, ambiente, status, protocolo e documento.
4. Persistir retorno e atualizar a máquina de estados.
5. Reprocessar somente falhas elegíveis, com limite e backoff.
6. Enviar divergências para fila de revisão.
7. Emitir relatório de pendências e métricas de rejeição.
