# Regra de Faturamento ACID

Pedido de venda e documento fiscal são entidades diferentes. Um pedido pode ser faturado, cancelado ou convertido em NF-e/NFC-e conforme a política operacional.

A transação de faturamento deve proteger a consistência local: validar estoque, criar ou confirmar saída do Kardex, criar contas a receber e alterar o estado do pedido dentro de uma unidade transacional. Se qualquer operação local falhar, executar rollback.

Chamadas à SEFAZ ou à API fiscal externa não devem permanecer abertas dentro da transação longa do banco. Usar outbox/evento transacional: confirmar fatos locais, publicar evento com chave idempotente e processar envio externo de forma assíncrona e reconciliável.
