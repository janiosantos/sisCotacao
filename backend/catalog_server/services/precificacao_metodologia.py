"""Cálculo puro da metodologia de formação de preço da planilha de referência.

O cálculo não acessa banco nem regras fiscais. Isso torna a memória de cálculo
testável e deixa explícito o que é premissa comercial e o que é resultado.
Percentuais são recebidos no formato humano (ex.: 25 para 25%).
"""
from __future__ import annotations

from math import isfinite


ATIVIDADE_REFERENCIAS = {
    "comercio": {
        "nome": "Comércio",
        "despesa_fixa_pct": 25.0,
        "despesa_variavel_pct": 70.0,
        "lucratividade_pct": 10.0,
    },
    "servicos": {
        "nome": "Serviços",
        "despesa_fixa_pct": 40.0,
        "despesa_variavel_pct": 40.0,
        "lucratividade_pct": 20.0,
    },
    "industria": {
        "nome": "Indústria",
        "despesa_fixa_pct": 30.0,
        "despesa_variavel_pct": 60.0,
        "lucratividade_pct": 10.0,
    },
}


def _pct(value: float | int | None, label: str) -> float:
    result = float(value or 0)
    if not isfinite(result) or result < 0 or result > 100:
        raise ValueError(f"{label} deve estar entre 0 e 100")
    return result


def calcular(
    custo_liquido: float,
    *,
    embalagem_unitaria: float = 0.0,
    frete_unitario: float = 0.0,
    frete_pct: float = 0.0,
    cartao_pct: float = 0.0,
    impostos_pct: float = 0.0,
    comissao_pct: float = 0.0,
    despesas_variaveis_pct: float = 0.0,
    despesas_fixas_pct: float = 0.0,
    margem_pct: float = 0.0,
    cenario_tributario: str = "atual",
    reforma_tributaria_pct: float = 0.0,
) -> dict:
    """Calcula preço pelo divisor e devolve a memória de cálculo completa."""
    custo = float(custo_liquido)
    embalagem = float(embalagem_unitaria or 0)
    frete = float(frete_unitario or 0)
    if not isfinite(custo) or custo < 0:
        raise ValueError("custo_liquido deve ser maior ou igual a zero")
    if not isfinite(embalagem) or embalagem < 0 or not isfinite(frete) or frete < 0:
        raise ValueError("embalagem e frete unitários devem ser maiores ou iguais a zero")

    percentuais = {
        "frete": _pct(frete_pct, "frete_pct"),
        "cartao": _pct(cartao_pct, "cartao_pct"),
        "impostos": _pct(impostos_pct, "impostos_pct"),
        "comissao": _pct(comissao_pct, "comissao_pct"),
        "despesas_variaveis": _pct(despesas_variaveis_pct, "despesas_variaveis_pct"),
        "despesas_fixas": _pct(despesas_fixas_pct, "despesas_fixas_pct"),
        "margem": _pct(margem_pct, "margem_pct"),
    }
    reforma_pct = _pct(reforma_tributaria_pct, "reforma_tributaria_pct")
    if cenario_tributario not in ("atual", "reforma"):
        raise ValueError("cenario_tributario deve ser atual ou reforma")

    custo_formacao = round(custo + embalagem + frete, 2)
    custos_percentuais = (
        percentuais["frete"]
        + percentuais["cartao"]
        + percentuais["impostos"]
        + percentuais["comissao"]
        + percentuais["despesas_variaveis"]
        + percentuais["despesas_fixas"]
    )
    tributo_fora_divisor = reforma_pct if cenario_tributario == "reforma" else 0.0
    percentual_divisor = custos_percentuais + percentuais["margem"]
    divisor = 1 - percentual_divisor / 100
    preco_sem_tributos = None
    preco_com_tributos = None
    preco_minimo_sem_tributos = None
    preco_minimo = None
    markup_multiplicador = None
    tributos_valor = 0.0
    alertas: list[str] = []

    if custo_formacao <= 0:
        alertas.append("Informe um custo de aquisição para formar o preço.")
    if divisor <= 0:
        alertas.append("A soma dos percentuais do divisor deve ser menor que 100%.")
    else:
        preco_sem_tributos = round(custo_formacao / divisor, 2)
        tributos_valor = round(preco_sem_tributos * tributo_fora_divisor / 100, 2)
        preco_com_tributos = round(preco_sem_tributos + tributos_valor, 2)
        markup_multiplicador = round(1 / divisor, 6)

        divisor_minimo = 1 - custos_percentuais / 100
        if divisor_minimo > 0:
            preco_minimo_sem_tributos = round(custo_formacao / divisor_minimo, 2)
            preco_minimo = round(
                preco_minimo_sem_tributos
                + preco_minimo_sem_tributos * tributo_fora_divisor / 100,
                2,
            )

    if cenario_tributario == "reforma" and reforma_pct <= 0:
        alertas.append("Cenário Reforma selecionado sem IBS/CBS configurado.")
    if percentuais["impostos"] > 0 and cenario_tributario == "reforma":
        alertas.append("Confira se os impostos atuais não estão duplicados com IBS/CBS.")

    margem_efetiva = percentuais["margem"] if preco_sem_tributos is not None else None
    markup_efetivo = (
        round((preco_sem_tributos / custo_formacao - 1) * 100, 2)
        if preco_sem_tributos is not None and custo_formacao > 0
        else None
    )
    return {
        "metodologia": "divisor",
        "cenario_tributario": cenario_tributario,
        "custo_aquisicao": round(custo, 2),
        "adicionais": {
            "embalagem_unitaria": round(embalagem, 2),
            "frete_unitario": round(frete, 2),
        },
        "custo_formacao": custo_formacao,
        "percentuais": {
            **percentuais,
            "custos_percentuais": round(custos_percentuais, 4),
            "tributo_fora_divisor": round(tributo_fora_divisor, 4),
            "total_divisor": round(percentual_divisor, 4),
        },
        "divisor": round(divisor, 6),
        "markup_multiplicador": markup_multiplicador,
        "preco_minimo_sem_tributos": preco_minimo_sem_tributos,
        "preco_minimo": preco_minimo,
        "preco_sem_tributos": preco_sem_tributos,
        "tributos_valor": tributos_valor,
        "preco_com_tributos": preco_com_tributos,
        "preco_sugerido": preco_com_tributos,
        "margem_efetiva_pct": margem_efetiva,
        "markup_efetivo_pct": markup_efetivo,
        "alertas": alertas,
    }
