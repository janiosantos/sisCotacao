"""Domínio de estoque por eventos auditáveis (ADR 0003)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MovimentoEstoque:
    """Fato imutável de estoque com idempotência e origem rastreável."""

    deposito_id: int
    variante_id: int
    tipo: str  # entrada|saida|ajuste|transferencia|inventario|reserva|liberacao
    quantidade: str  # Decimal serializado (NUMERIC(14,3))
    idempotency_key: str  # UNIQUE — retrida ignora
    origem_tipo: str = ""  # documento de negócio (ex.: orcamento)
    origem_id: int | None = None
    observacao: str = ""
