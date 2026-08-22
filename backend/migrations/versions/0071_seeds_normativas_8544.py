"""Migração 0071 — Seeds normativas: cabos/fios elétricos NCM 8544 (MG, Simples).

Fontes: docs/fiscal/legislacao/validacoes/2026-08-cabos-eletricos.md
  - Consulta de Contribuinte nº 105/2021 (SEF/MG)
  - Protocolo ICMS 8/10 (CONFAZ)
Estado PUBLISHED; motor v2 continua atrás da flag FISCAL_ENGINE_V2.
"""
from __future__ import annotations

VERSION = 71
RISCO = "rotina"
NAME = "seeds_normativas_8544"

MUDANCA = {
    "o_que": [
        "Semeia 2 regras PUBLISHED p/ NCM 8544 MG-Simples: substituído já retido (5405/500) e exceção automotiva (5102/102)",
        "Registra ncm_version 8544.20.00 / 8544.30.00 / 8544.49.00 com fontes",
    ],
    "porque": [
        "Validação normativa do dossiê 2026-08-cabos-eletricos.md "
        "(Consulta SEF/MG 105/2021 + Protocolo ICMS 8/10)"
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM fiscal_engine_rule WHERE code = 'norma-8544-substituido-retido'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # NCMs versionados com fonte (URL parametrizada: '%s' no literal
        # conflita com o placeholder do shim)
        fonte_consulta = (
            "https://www.legisweb.com.br/legislacao/?id=415741"
        )
        for codigo, desc in (
            ("8544.20.00", "Cabos coaxiais e outros condutores elétricos coaxiais"),
            ("8544.30.00", "Jogos de fios para velas de ignição e outros jogos de fio"),
            ("8544.49.00", "Fios e cabos elétricos, para tensão não superior a 1000V"),
        ):
            conn.execute(
                """
                INSERT INTO ncm_version (codigo, descricao, fonte_url, vigencia_inicio)
                VALUES (%s, %s, %s, CURRENT_DATE)
                ON CONFLICT (codigo, vigencia_inicio) DO NOTHING
                """,
                (codigo, desc, fonte_consulta),
            )

        # Regra 1: substituído já retido -> 5405 / CSOSN 500
        rid1 = _regra(conn, code="norma-8544-substituido-retido",
                      nome="MG · Simples · 8544 revenda substituído já retido",
                      prioridade=900,
                      legal="Consulta SEF/MG 105/2021 + RICMS/MG Anexo VII Cap.12 item 7.0",
                      fonte="https://www.legisweb.com.br/legislacao/?id=415741")
        vid1 = _versao(conn, rid1)
        _condicoes(conn, vid1, {
            "tax_regime": "simples_nacional",
            "uf_origin": "MG",
            "uf_destination": "MG",
            "operation_type": "venda",
            "ncm": "8544",
        })
        conn.execute(
            "INSERT INTO fiscal_engine_rule_result"
            " (version_id, cfop, csosn, cst_icms, modalidade_st)"
            " VALUES (%s, '5405', '500', '', 'substituido_ja_retido')"
            " ON CONFLICT (version_id) DO NOTHING",
            (vid1,),
        )

        # Regra 2: exceção uso automotivo -> tributação normal no DAS
        rid2 = _regra(conn, code="norma-8544-automotivo-excecao",
                      nome="MG · Simples · 8544 uso automotivo (exceção ST)",
                      prioridade=950,
                      legal="Art. 58-A + itens 72.0/73.0 Cap.1 Parte 2 (CEST 01.072.00/01.073.00)",
                      fonte="https://www.legisweb.com.br/legislacao/?id=415741")
        vid2 = _versao(conn, rid2)
        _condicoes(conn, vid2, {
            "tax_regime": "simples_nacional",
            "uf_origin": "MG",
            "uf_destination": "MG",
            "operation_type": "venda",
            "extras_uso_automotivo": "sim",
        })
        conn.execute(
            "INSERT INTO fiscal_engine_rule_result"
            " (version_id, cfop, csosn, cst_icms)"
            " VALUES (%s, '5102', '102', '')"
            " ON CONFLICT (version_id) DO NOTHING",
            (vid2,),
        )
    finally:
        conn.autocommit = ac


def _regra(conn, *, code: str, nome: str, prioridade: int,
           legal: str, fonte: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO fiscal_engine_rule (code, nome, tipo, prioridade, estado)
        VALUES (%s, %s, 'operacao', %s, 'PUBLISHED')
        ON CONFLICT (code) DO UPDATE SET nome = EXCLUDED.nome,
          atualizado_em = now()
        RETURNING id
        """,
        (code, nome, prioridade),
    )
    rid = int(cur.fetchone()[0])
    conn.execute(
        "UPDATE fiscal_engine_rule_version SET legal_reference=%s, source_url=%s"
        " WHERE rule_id=%s AND version=1",
        (legal, fonte, rid),
    )
    return rid


def _versao(conn, rid: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO fiscal_engine_rule_version
            (rule_id, version, valid_from, legal_reference)
        VALUES (%s, 1, CURRENT_DATE, 'ver dossiê 2026-08-cabos-eletricos')
        ON CONFLICT (rule_id, version) DO UPDATE SET valid_from = CURRENT_DATE
        RETURNING id
        """,
        (rid,),
    )
    return int(cur.fetchone()[0])


def _condicoes(conn, vid: int, condicoes: dict[str, str]) -> None:
    """Substitui as condições da versão pelas informadas."""
    conn.execute(
        "DELETE FROM fiscal_engine_rule_condition WHERE version_id=%s", (vid,)
    )
    extras_key = "extras_uso_automotivo"
    for campo, valor in condicoes.items():
        if campo == extras_key:
            # condição sobre o campo extra registrado no contexto
            conn.execute(
                "INSERT INTO fiscal_engine_rule_condition"
                " (version_id, campo, operador, valor) VALUES (%s,%s,'igual',%s)",
                (vid, campo, valor),
            )
            continue
        operador = "prefixo" if campo == "ncm" else "igual"
        conn.execute(
            "INSERT INTO fiscal_engine_rule_condition"
            " (version_id, campo, operador, valor) VALUES (%s,%s,%s,%s)",
            (vid, campo, operador, valor),
        )


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        for code in ("norma-8544-substituido-retido", "norma-8544-automotivo-excecao"):
            conn.execute(
                "DELETE FROM fiscal_engine_rule WHERE code=%s", (code,)
            )
    finally:
        conn.autocommit = ac
