# Workflow: Movimento de Estoque

1. Identificar evento, origem, variante, quantidade, unidade e depósito.
2. Validar disponibilidade, lotes/séries e permissões.
3. Reservar ou movimentar dentro de transação idempotente.
4. Atualizar projeção de saldo.
5. Gerar evento contábil quando aplicável.
6. Reconciliar saldo e registrar auditoria.
7. Tratar falha parcial com retry seguro ou compensação.
