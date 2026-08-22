# Regra Operacional — Faturamento ACID e Outbox

A transação de banco deve garantir atomicidade entre estado local do pedido, baixa/reserva de estoque e contas a receber. A comunicação externa ocorre depois do commit, por outbox transacional.

Se faltar estoque ou uma constraint falhar, não deve existir pedido faturado sem movimento, nem movimento sem origem, nem título a receber sem pedido. Caso o envio externo falhe, o estado local permanece pendente de emissão e pode ser reconciliado sem duplicar documento.
