# ADR 0003 — Estoque por Eventos Auditáveis

## Status
Aceito (v2.3.0)

## Decisão
Saldo é DERIVADO/RECONCILIÁVEL a partir de fatos: movimentos, reservas,
ajustes e inventários com idempotência e origem rastreável. Edição direta
de saldo deixa de ser operação normal.
