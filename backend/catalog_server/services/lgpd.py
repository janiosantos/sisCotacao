"""LGPD (ADM-003 / DECISAO-010): mascaramento de PII e dados financeiros.

Campos classificados como sensíveis têm a exposição mascarada em logs,
auditoria, relatórios e respostas que não precisam do valor completo.
"""

from __future__ import annotations

import re

_CAMPOS_PII = {
    "doc", "cpf", "cnpj", "cnpj_cpf", "cpf_cnpj", "cpfcnpj", "cliente_doc",
    "email", "telefone", "whatsapp", "cep", "senha", "senha_hash", "token",
    "cartao", "numero_cartao", "cv", "pan", "password", "secret",
}


def mascarar(texto: str) -> str:
    """Mascara CPF/CNPJ, telefone, e-mail e chaves longas num texto."""
    if not texto:
        return texto or ""
    t = texto
    # e-mail: primeiro char + ***@domínio
    t = re.sub(r"([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", r"\1***\2", t)
    # CPF/CNPJ (11/14 dígitos, com . / -)
    t = re.sub(r"\b(\d{3})[\d./\-]{5,11}(\d{2})\b", r"\1******\2", t)
    # telefone (11 dígitos)
    t = re.sub(r"\b\(?(\d{2})\)?[\s.-]?(\d{4})\d{4}\b", r"(\1) \2-****", t)
    return t


def mascarar_valor(chave: str, valor):
    """Mascara um campo sensível; senão devolve o valor original."""
    if valor is None:
        return None
    if chave.lower() in _CAMPOS_PII:
        if isinstance(valor, dict):
            return {"masked": True}
        texto = str(valor)
        mascarado = mascarar(texto)
        if mascarado != texto or len(texto) <= 4:
            return mascarado
        return "***"  # valor curto sem padrão detectável (ex.: hash)
    return valor


def mascarar_dict(dados: dict | None) -> dict | None:
    if not dados:
        return dados
    out = {}
    for k, v in dados.items():
        out[k] = mascarar_valor(k, v)
    return out


def is_sensivel(chave: str) -> bool:
    return chave.lower() in _CAMPOS_PII