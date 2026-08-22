"""Engines fiscais separadas por tributo (skill fiscal-mg §5-6, fiscal-engine).

Engenharia pura: recebem parâmetros EXPLÍCITOS (base, alíquota, método) e
devolvem valores em Decimal quantizados. Nenhuma alíquota legal vive aqui —
quem fornece números é a camada de regras versionadas.

Separado por design (§20): icms_proprio e icms_st nunca se misturam;
DIFAL de entrada e saída são cálculos distintos.
"""
from __future__ import annotations

from decimal import Decimal

from catalog_server.fiscal.decimais import aliquota, dinheiro, to_decimal

D = Decimal("0")
UM = Decimal("1")
CEM = Decimal("100")


def _d(valor) -> Decimal:
    return to_decimal(valor) or D


def _pct4(valor) -> Decimal:
    return aliquota(valor)


# ─── ICMS próprio ──────────────────────────────────────────────────────────


def icms_proprio(
    base: Decimal,
    aliquota: Decimal,
    reducao_pct: Decimal | None = None,
) -> dict:
    """ICMS próprio: base com redução opcional, depois alíquota."""
    b = _d(base)
    red = _pct4(reducao_pct or 0)
    base_efetiva = dinheiro(b * (UM - red / CEM))
    a = _pct4(aliquota)
    valor = dinheiro(base_efetiva * a / CEM)
    return {
        "base": base_efetiva,
        "aliquota": a,
        "reducao_pct": red,
        "valor": valor,
    }


# ─── ICMS-ST ───────────────────────────────────────────────────────────────


def icms_st(
    valor_operacao: Decimal,
    *,
    metodo: str,
    mva_pct: Decimal | None = None,
    preco_fixado: Decimal | None = None,
    icms_inter: Decimal | None = None,
    aliquota_interna: Decimal,
    ipi: Decimal | None = None,
    frete: Decimal | None = None,
    seguro: Decimal | None = None,
    outras_despesas: Decimal | None = None,
    base_reducao_st_pct: Decimal | None = None,
) -> dict:
    """ICMS-ST com métodos previstos: 'mva_original', 'mva_ajustada',
    'preco_fixado'. Sempre separa icms_proprio (informado) do ST calculado.

    - mva_original : base ST = operação (+IPI/frete/seg/outros) × (1 + MVA orig)
    - mva_ajustada : idem, mas MVA AJUSTADA já considera o ICMS interstatual
                     (o ajuste numérico chega pronto via mva_pct pela regra)
    - preco_fixado : base ST = preço fixado/PMPF informado (+ componentes)
    """
    vo = _d(valor_operacao)
    componentes = sum(_d(x) for x in (ipi, frete, seguro, outras_despesas))
    proprio = _d(icms_inter)

    if metodo == "preco_fixado":
        base_st = _d(preco_fixado) + componentes
        metodo_usado = "preco_fixado"
    elif metodo in ("mva_original", "mva_ajustada"):
        mva = _pct4(mva_pct or 0)
        base_sem_st = vo + componentes
        base_st = dinheiro(base_sem_st * (UM + mva / CEM))
        metodo_usado = metodo
    else:
        raise ValueError(f"metodo ST desconhecido: {metodo}")

    red = _pct4(base_reducao_st_pct or 0)
    if red > 0:
        base_st = dinheiro(base_st * (UM - red / CEM))

    ai = _pct4(aliquota_interna)
    st_bruto = dinheiro(base_st * ai / CEM)
    icms_st_value = dinheiro(st_bruto - proprio) if st_bruto > proprio else D("0.00")

    return {
        "metodo": metodo_usado,
        "icms_proprio": proprio,
        "icms_st_base": base_st,
        "aliquota_interna": ai,
        "icms_st_value": icms_st_value,
    }


# ─── DIFAL ─────────────────────────────────────────────────────────────────


def difal_entrada(
    valor_operacao: Decimal,
    icms_origem: Decimal,
    aliquota_interna: Decimal,
    *,
    por_dentro: bool = True,
) -> dict:
    """DIFAL de ENTRADA (uso/consumo, ativo, revenda conforme regra).

    Cálculo POR DENTRO quando a legislação determinar (fórmula conceitual
    do kit §6):
        valor_sem_icms_origem = valor_operacao - icms_origem
        base_destino          = valor_sem_icms_origem / (1 - aliquota_interna)
        difal                 = base_destino × aliquota_interna - icms_origem
    """
    vo = _d(valor_operacao)
    inter = _d(icms_origem)
    ai = _pct4(aliquota_interna)

    if por_dentro:
        sem_origem = vo - inter
        base_destino = dinheiro(sem_origem / (UM - ai / CEM)) if ai < CEM else D("0.00")
    else:
        base_destino = dinheiro(vo)

    difal = dinheiro(base_destino * ai / CEM - inter)
    return {
        "modalidade": "entrada",
        "por_dentro": por_dentro,
        "base_destino": base_destino,
        "aliquota_interna": ai,
        "icms_origem": inter,
        "difal_value": difal,
    }


def difal_saida(
    base: Decimal,
    aliquota_interestadual: Decimal,
    aliquota_interna: Decimal,
    fcp_rate: Decimal | None = None,
) -> dict:
    """DIFAL de SAÍDA — consumidor final não contribuinte de outra UF.

    FCP segregado da parcela interestadual quando a regra informar rate.
    """
    b = _d(base)
    inter = _pct4(aliquota_interestadual)
    interna = _pct4(aliquota_interna)
    fcp = _pct4(fcp_rate or 0)

    icms_inter_value = dinheiro(b * inter / CEM)
    base_fcp = dinheiro(b * fcp / CEM) if fcp > 0 else D("0.00")
    difal_base = dinheiro(b * (interna - fcp) / CEM)
    difal_value = dinheiro(difal_base - icms_inter_value)

    return {
        "modalidade": "saida",
        "base": b,
        "aliquota_interestadual": inter,
        "aliquota_interna": interna,
        "icms_inter_value": icms_inter_value,
        "difal_base": difal_base,
        "difal_value": difal_value,
        "fcp_rate": fcp,
        "fcp_value": base_fcp,
    }
