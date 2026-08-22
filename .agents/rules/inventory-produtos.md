# Regra de Estoque

Estoque deve ser controlado por `StockMovement`, com tipo, quantidade, unidade, depósito, lote/série quando aplicável, custo, origem e usuário. O saldo disponível deve distinguir estoque físico, reservado, disponível, bloqueado e em trânsito.

Toda entrada, saída, transferência, ajuste, devolução, reserva e baixa deve ser idempotente e auditável. Não aceitar saldo negativo sem política explícita por depósito e operação. Inventários devem gerar contagem, divergência, aprovação e movimento de ajuste.

Custo médio, FIFO ou outro método deve ser parametrizado por empresa e período; nunca misturar métodos no mesmo cálculo sem decisão documentada.
