"""Schemas e contratos (ARC-002): validação declarativa de payload de endpoints
críticos — enum, decimal, datas, ids, limites e campos desconhecidos.
"""

from __future__ import annotations

from datetime import date, datetime


def validar(payload: dict, schema: dict) -> tuple[dict, dict]:
    """Valida `payload` contra `schema` (campo → regras). Retorna (erros, limpo).

    Regras: tipo (int|float|string|date|bool), requerido, enum, min/max,
    permitir_extra (False rejeita campos desconhecidos quando seguro).
    """
    erros: dict[str, str] = {}
    limpo: dict = {}
    chaves = set(schema) if not any(r.get("permitir_extra") for r in schema.values()) else set()
    for campo, regras in schema.items():
        chaves.add(campo)
        valor = payload.get(campo)
        requerido = regras.get("requerido", False)
        if valor is None or valor == "":
            if requerido:
                erros[campo] = "obrigatório"
            continue
        tipo = regras.get("tipo", "string")
        if tipo == "int":
            try:
                valor = int(valor)
            except (TypeError, ValueError):
                erros[campo] = "deve ser inteiro"
                continue
        elif tipo == "float":
            try:
                valor = float(valor)
            except (TypeError, ValueError):
                erros[campo] = "deve ser número"
                continue
        elif tipo == "date":
            try:
                if isinstance(valor, str):
                    valor = date.fromisoformat(valor[:10])
                limpo[campo] = valor.isoformat() if hasattr(valor, "isoformat") else valor
                continue
            except ValueError:
                erros[campo] = "data inválida (YYYY-MM-DD)"
                continue
        elif tipo == "bool":
            if isinstance(valor, str):
                valor = valor.lower() in ("1", "true", "sim")
            elif not isinstance(valor, bool):
                erros[campo] = "deve ser booleano"
                continue
        if "enum" in regras and valor not in regras["enum"]:
            erros[campo] = f"deve ser um de: {', '.join(map(str, regras['enum']))}"
            continue
        if tipo in ("int", "float"):
            if "min" in regras and valor < regras["min"]:
                erros[campo] = f"deve ser >= {regras['min']}"
            if "max" in regras and valor > regras["max"]:
                erros[campo] = f"deve ser <= {regras['max']}"
        limpo[campo] = valor
    extras = [k for k in payload if k not in chaves]
    if extras:
        erros["_extra"] = f"campos desconhecidos: {', '.join(extras)}"
    return erros, limpo


def aplicar(payload: dict, schema: dict) -> tuple[dict | None, dict]:
    """Conveniência para endpoints: retorna (erros or None, limpo)."""
    erros, limpo = validar(payload or {}, schema)
    return (erros or None), limpo