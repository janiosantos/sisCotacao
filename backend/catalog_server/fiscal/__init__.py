"""Domínio Fiscal — contratos centrais do Motor Fiscal.

Estrutura por responsabilidade (skill fiscal-engine):
    contexto.py   FiscalContext
    resultado.py  FiscalResult + EstadoFiscal
    decimais.py   política de precisão (Decimal/NUMERIC)

Regra do kit: dinheiro e tributo SEMPRE em Decimal no backend e NUMERIC no PG.
"""
from catalog_server.fiscal.contexto import FiscalContext
from catalog_server.fiscal.estados import EstadoFiscal
from catalog_server.fiscal.resultado import FiscalResult

__all__ = ["FiscalContext", "EstadoFiscal", "FiscalResult"]
