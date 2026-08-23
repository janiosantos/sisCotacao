"""Migração 0072 — MVA confirmada (Anexo VII Cap.12) + regras 8536/8516.

- norma-8544-substituido-retido: registra mva=40.0000 (item 7.0, acesso
  23/08/2026 em anexovii2023_5.html);
- Semeia 8536 (MVA 40, item 4.0) e 8516 (MVA 45, item 2.0) MG-Simples revenda
  substituído retido — mesmo enquadramento estrutural.
"""
from __future__ import annotations

VERSION = 72
RISCO = "rotina"
NAME = "mva_confirmada_8544"

MUDANCA = {
    "o_que": [
        "Registra mva=40 na regra norma-8544-substituido-retido",
        "Semeia regras 8536 (40%) e 8516 (45%) MG-Simples revenda substituído retido",
    ],
    "porque": [
        "Validação normativa no Anexo VII Parte 2 Cap.12 (acesso 23/08/2026)"
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT mva FROM fiscal_engine_rule_result WHERE version_id IN"
        " (SELECT id FROM fiscal_engine_rule_version WHERE rule_id IN"
        "  (SELECT id FROM fiscal_engine_rule WHERE code='norma-8544-substituido-retido'))"
    ).fetchone()
    return row is not None and row[0] == 40


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            UPDATE fiscal_engine_rule_result SET mva = 40.0000
            WHERE version_id IN (
                SELECT id FROM fiscal_engine_rule_version
                WHERE rule_id IN (
                    SELECT id FROM fiscal_engine_rule
                    WHERE code='norma-8544-substituido-retido'
                )
            )
            """
        )
        for ncm, mva, code in (
            ("8536", "40", "norma-8536-substituido-retido"),
            ("8516", "45", "norma-8516-substituido-retido"),
        ):
            cur = conn.execute(
                """
                INSERT INTO fiscal_engine_rule (code, nome, tipo, prioridade, estado)
                VALUES (%s, %s, 'operacao', 900, 'PUBLISHED')
                ON CONFLICT (code) DO NOTHING RETURNING id
                """,
                (code, f"MG · Simples · {ncm} revenda substituído retido"),
            )
            row = cur.fetchone() if hasattr(cur, "fetchone") else None
            rid = int(row[0]) if row else _rid_por_code(conn, code)
            vid = _versao(conn, rid)
            conn.execute(
                "DELETE FROM fiscal_engine_rule_condition WHERE version_id=%s",
                (vid,),
            )
            for campo in ("tax_regime", "uf_origin", "uf_destination", "operation_type"):
                valor = {
                    "tax_regime": "simples_nacional",
                    "uf_origin": "MG",
                    "uf_destination": "MG",
                    "operation_type": "venda",
                }[campo]
                conn.execute(
                    "INSERT INTO fiscal_engine_rule_condition"
                    " (version_id, campo, operador, valor) VALUES (%s, %s, 'igual', %s)",
                    (vid, campo, valor),
                )
            conn.execute(
                """
                INSERT INTO fiscal_engine_rule_result
                    (version_id, cfop, csosn, modalidade_st, mva, aliquota_icms_st)
                VALUES (%s, '5405', '500', 'substituido_ja_retido', %s, 0)
                ON CONFLICT (version_id) DO UPDATE SET mva = EXCLUDED.mva
                """,
                (vid, mva),
            )
            # NCM versionado com fonte oficial
            conn.execute(
                """
                INSERT INTO ncm_version (codigo, descricao, fonte_url, vigencia_inicio)
                VALUES (%s, 'Ver Anexo VII Cap.12 item correspondente',
                        'https://www.fazenda.mg.gov.br/empresas/legislacao_tributaria/ricms_2023_seco/anexovii2023_5.html',
                        CURRENT_DATE)
                ON CONFLICT (codigo, vigencia_inicio) DO NOTHING
                """,
                (ncm,),
        )
    finally:
        conn.autocommit = ac


def _rid_por_code(conn, code: str) -> int:
    return int(
        conn.execute(
            "SELECT id FROM fiscal_engine_rule WHERE code=%s", (code,)
        ).fetchone()[0]
    )


def _versao(conn, rid: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO fiscal_engine_rule_version
            (rule_id, version, valid_from, legal_reference)
        VALUES (%s, 1, CURRENT_DATE,
                'Anexo VII RICMS/MG Cap.12 (acesso 23/08/2026)')
        ON CONFLICT (rule_id, version) DO UPDATE SET valid_from = CURRENT_DATE
        RETURNING id
        """,
        (rid,),
    )
    return int(cur.fetchone()[0])


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        for code in ("norma-8536-substituido-retido", "norma-8516-substituido-retido"):
            conn.execute("DELETE FROM fiscal_engine_rule WHERE code=%s", (code,))
    finally:
        conn.autocommit = ac
