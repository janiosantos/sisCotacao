# Workflow: Contabilização

1. Receber evento de negócio com origem única.
2. Identificar matriz contábil vigente.
3. Resolver contas e dimensões.
4. Calcular valores e validar período aberto.
5. Criar partidas equilibradas e idempotentes.
6. Vincular lançamento ao evento, documento e usuário/processo.
7. Bloquear alteração direta após fechamento; usar estorno.
