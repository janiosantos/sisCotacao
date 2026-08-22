# Regra de Kardex e Ledger de Estoque

A tabela `estoque_movimentos` é append-only. Correções produzem movimentos de estorno relacionados ao movimento original; não se corrige histórico com `UPDATE` destrutivo.

O saldo disponível é `quantidade_fisica - quantidade_reservada`, respeitando unidade, depósito, lote e série. Reserva de pedido não reduz o físico; retirada confirmada gera saída física.

Toda movimentação deve possuir `idempotency_key`, origem, usuário/processo, data efetiva, direção, quantidade positiva, custo unitário e correlação. A projeção `estoque_saldos` deve ser reconciliável com o ledger.

O custo médio deve ser recalculado nas entradas elegíveis conforme política da empresa. A baixa de venda deve capturar o custo aplicado para permitir o CMV e a contabilização; não recalcular o custo histórico de uma venda já contabilizada.
