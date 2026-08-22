# Workflow: Pedido até Faturamento

1. Criar pedido e itens com preço e descontos versionados.
2. Reservar estoque, se a política exigir.
3. Validar cadastro, cliente, endereço, natureza e contexto fiscal.
4. Resolver TaxRule e congelar o snapshot dos itens.
5. Confirmar faturamento em transação local com baixa/reserva, contas a receber e estado do pedido.
6. Publicar evento de emissão via outbox.
7. Transmitir com idempotência e atualizar o estado por retorno confirmado.
8. Reconciliar estoque, financeiro, fiscal e contabilidade.
