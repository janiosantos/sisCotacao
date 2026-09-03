"""Persistência das premissas gerais da formação de preço."""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services.precificacao_metodologia import ATIVIDADE_REFERENCIAS


_DEFAULTS = {
    "id": 1,
    "faturamento_mensal": 0.0,
    "despesa_fixa_mensal": 0.0,
    "despesa_variavel_mensal": 0.0,
    "imposto_simples_pct": 0.0,
    "imposto_icms_pct": 0.0,
    "imposto_pis_pct": 0.0,
    "imposto_cofins_pct": 0.0,
    "imposto_ir_pct": 0.0,
    "imposto_csll_pct": 0.0,
    "ibs_pct": 0.0,
    "cbs_pct": 0.0,
    "taxa_cartao_pct": 0.0,
    "atividade": "comercio",
    "usar_referencia_atividade": True,
    "cenario_tributario": "atual",
    "competencia_precificacao": None,
    "usar_competencia_aprovada": True,
    "incluir_despesas_variaveis_rateadas": False,
}


def _flag(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    return value is True or value == 1 or str(value).lower() in {"1", "true", "on", "sim"}


def obter() -> dict:
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM precificacao_configuracao WHERE id=1").fetchone()
    result = {**_DEFAULTS, **(dict(row) if row else {})}
    for key in (
        "faturamento_mensal", "despesa_fixa_mensal", "despesa_variavel_mensal",
        "imposto_simples_pct", "imposto_icms_pct", "imposto_pis_pct",
        "imposto_cofins_pct", "imposto_ir_pct", "imposto_csll_pct",
        "ibs_pct", "cbs_pct", "taxa_cartao_pct",
    ):
        result[key] = float(result.get(key) or 0)
    result["impostos_atual_pct"] = round(
        sum(float(result.get(k) or 0) for k in (
            "imposto_simples_pct", "imposto_icms_pct", "imposto_pis_pct",
            "imposto_cofins_pct", "imposto_ir_pct", "imposto_csll_pct",
        )),
        4,
    )
    result["reforma_tributaria_pct"] = round(
        float(result.get("ibs_pct") or 0) + float(result.get("cbs_pct") or 0), 4
    )
    faturamento = float(result.get("faturamento_mensal") or 0)
    result["despesa_fixa_real_pct"] = (
        round(float(result.get("despesa_fixa_mensal") or 0) / faturamento * 100, 4)
        if faturamento > 0 else None
    )
    result["despesa_variavel_real_pct"] = (
        round(float(result.get("despesa_variavel_mensal") or 0) / faturamento * 100, 4)
        if faturamento > 0 else None
    )
    result["referencia_atividade"] = ATIVIDADE_REFERENCIAS.get(
        result.get("atividade"), ATIVIDADE_REFERENCIAS["comercio"]
    )
    result["incluir_despesas_variaveis_rateadas"] = _flag(result.get("incluir_despesas_variaveis_rateadas"))
    result["usar_competencia_aprovada"] = _flag(result.get("usar_competencia_aprovada"), True)
    return result


def salvar(data: dict) -> dict:
    numeric = (
        "faturamento_mensal", "despesa_fixa_mensal", "despesa_variavel_mensal",
        "imposto_simples_pct", "imposto_icms_pct", "imposto_pis_pct",
        "imposto_cofins_pct", "imposto_ir_pct", "imposto_csll_pct",
        "ibs_pct", "cbs_pct", "taxa_cartao_pct",
    )
    values = {key: float(data.get(key, 0) or 0) for key in numeric}
    for key, value in values.items():
        if value < 0 or ("pct" in key and value > 100):
            raise ValueError(f"{key} inválido")
    atividade = data.get("atividade") or "comercio"
    if atividade not in ATIVIDADE_REFERENCIAS:
        raise ValueError("atividade deve ser comercio, servicos ou industria")
    cenario = data.get("cenario_tributario") or "atual"
    if cenario not in ("atual", "reforma"):
        raise ValueError("cenario_tributario deve ser atual ou reforma")
    usar_referencia = _flag(data.get("usar_referencia_atividade"), True)
    comp = data.get("competencia_precificacao") or None
    if comp:
        from catalog_server.services.classificacao_financeira import competencia
        comp = competencia(str(comp))
    with system_conn() as conn:
        conn.execute(
            """
            INSERT INTO precificacao_configuracao (
                id, faturamento_mensal, despesa_fixa_mensal, despesa_variavel_mensal,
                imposto_simples_pct, imposto_icms_pct, imposto_pis_pct,
                imposto_cofins_pct, imposto_ir_pct, imposto_csll_pct,
                ibs_pct, cbs_pct, taxa_cartao_pct, atividade,
                usar_referencia_atividade, cenario_tributario, atualizado_em
                , competencia_precificacao, usar_competencia_aprovada,
                incluir_despesas_variaveis_rateadas
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now(), ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                faturamento_mensal=EXCLUDED.faturamento_mensal,
                despesa_fixa_mensal=EXCLUDED.despesa_fixa_mensal,
                despesa_variavel_mensal=EXCLUDED.despesa_variavel_mensal,
                imposto_simples_pct=EXCLUDED.imposto_simples_pct,
                imposto_icms_pct=EXCLUDED.imposto_icms_pct,
                imposto_pis_pct=EXCLUDED.imposto_pis_pct,
                imposto_cofins_pct=EXCLUDED.imposto_cofins_pct,
                imposto_ir_pct=EXCLUDED.imposto_ir_pct,
                imposto_csll_pct=EXCLUDED.imposto_csll_pct,
                ibs_pct=EXCLUDED.ibs_pct, cbs_pct=EXCLUDED.cbs_pct,
                taxa_cartao_pct=EXCLUDED.taxa_cartao_pct,
                atividade=EXCLUDED.atividade,
                usar_referencia_atividade=EXCLUDED.usar_referencia_atividade,
                cenario_tributario=EXCLUDED.cenario_tributario,
                competencia_precificacao=EXCLUDED.competencia_precificacao,
                usar_competencia_aprovada=EXCLUDED.usar_competencia_aprovada,
                incluir_despesas_variaveis_rateadas=EXCLUDED.incluir_despesas_variaveis_rateadas,
                atualizado_em=EXCLUDED.atualizado_em
            """,
            (*[values[key] for key in numeric], atividade, usar_referencia, cenario,
             comp, _flag(data.get("usar_competencia_aprovada"), True),
             _flag(data.get("incluir_despesas_variaveis_rateadas"))),
        )
    return obter()


def despesas_fixas_pct(config: dict, usar_referencia: bool | None = None) -> tuple[float, str, str | None]:
    """Resolve percentual fixo e informa a origem para a memória de cálculo."""
    usar = config["usar_referencia_atividade"] if usar_referencia is None else usar_referencia
    if usar:
        ref = config["referencia_atividade"]
        return float(ref["despesa_fixa_pct"]), "referencia_atividade", None
    real = config.get("despesa_fixa_real_pct")
    if real is None:
        return 0.0, "sem_faturamento", "Informe o faturamento para calcular a despesa fixa real."
    return float(real), "despesas_reais", None
