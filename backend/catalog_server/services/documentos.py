"""Validacao de documentos de pessoas no limite do dominio."""
from __future__ import annotations

import re


def so_digitos(valor: object) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def normalizar_tipo_pessoa(valor: object) -> str:
    """Converte aliases legados para os valores canonicos ``f``/``j``."""
    tipo = str(valor or "f").strip().lower()
    if tipo in {"j", "pj", "juridica"}:
        return "j"
    return "f"


def validar_cpf(documento: object) -> bool:
    digitos = so_digitos(documento)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    total = sum(int(digitos[i]) * (10 - i) for i in range(9))
    primeiro = (total * 10) % 11
    primeiro = 0 if primeiro == 10 else primeiro
    if primeiro != int(digitos[9]):
        return False
    total = sum(int(digitos[i]) * (11 - i) for i in range(10))
    segundo = (total * 10) % 11
    segundo = 0 if segundo == 10 else segundo
    return segundo == int(digitos[10])


def validar_cnpj(documento: object) -> bool:
    digitos = so_digitos(documento)
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False

    def calcular(tamanho: int) -> int:
        soma = 0
        peso = 2
        for indice in range(tamanho - 1, -1, -1):
            soma += int(digitos[indice]) * peso
            peso = 2 if peso == 9 else peso + 1
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    return calcular(12) == int(digitos[12]) and calcular(13) == int(digitos[13])


def normalizar_e_validar_documento(documento: object, tipo_pessoa: object) -> tuple[str, str] | None:
    """Retorna ``(tipo, documento)`` ou ``None`` quando o campo esta vazio."""
    tipo = normalizar_tipo_pessoa(tipo_pessoa)
    digitos = so_digitos(documento)
    if not digitos:
        return None
    valido = validar_cnpj(digitos) if tipo == "j" else validar_cpf(digitos)
    if not valido:
        nome = "CNPJ" if tipo == "j" else "CPF"
        raise ValueError(f"{nome} invalido")
    return tipo, digitos
