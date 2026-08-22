---
name: kardex
description: Implementar estoque como ledger/Kardex append-only, com saldos, reservas, estornos, custo médio, CMV e reconciliação. Usar em entradas, saídas, transferências, ajustes ou inventários.
---

# Kardex

Modelar movimento como fato imutável. Usar transação local, lock ou controle de concorrência para evitar saldo incorreto. Separar físico, reservado, disponível, bloqueado e trânsito.

Para cada operação, testar idempotência, concorrência, rollback, estorno, custo aplicado e reconciliação entre movimentos e saldos.
