"""Migração 0065 — Motor fiscal v2: regras versionadas normalizadas (Expand).

Estrutura conforme `docs/fiscal/regras/modelo-dados-fiscal.md`, com estados
DRAFT→VALIDATED→PUBLISHED→SUPERSEDED→REVOKED e NUMERIC para alíquotas
(Regras de Banco #3-4). Legado (`fiscal_regra`) NÃO é tocado — o backfill cria
espelho PUBLISHED por linha ativa, idempotente por re-execução.
"""
from __future__ import annotations

VERSION = 65
RISCO = "critica"
NAME = "motor_versionado"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": [
        "Cria fiscal_engine_rule/_version/_condition/_result (estados DRAFT..REVOKED, alíquotas NUMERIC(9,4))",
        "Backfill espelhando fiscal_regra ativa como PUBLISHED version 1, critérios como condições",
    ],
    "porque": [
        "Motor fiscal versionado e auditável (ADR 0001): regras com vigência própria, fundamento legal e resultados normalizados",
        "Alíquotas em NUMERIC — proibição de float/double para tributos",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_name='fiscal_engine_rule_result'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fiscal_engine_rule (
                id BIGSERIAL PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL DEFAULT 'geral',
                prioridade INTEGER NOT NULL DEFAULT 500,
                estado TEXT NOT NULL DEFAULT 'PUBLISHED'
                    CHECK (estado IN ('DRAFT','VALIDATED','PUBLISHED','SUPERSEDED','REVOKED')),
                criado_em TIMESTAMP NOT NULL DEFAULT now(),
                atualizado_em TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fiscal_engine_rule_version (
                id BIGSERIAL PRIMARY KEY,
                rule_id BIGINT NOT NULL REFERENCES fiscal_engine_rule(id),
                version INTEGER NOT NULL,
                valid_from DATE NOT NULL,
                valid_to DATE,
                source_url TEXT,
                legal_reference TEXT NOT NULL DEFAULT '',
                criado_em TIMESTAMP NOT NULL DEFAULT now(),
                UNIQUE (rule_id, version)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fiscal_engine_rule_condition (
                id BIGSERIAL PRIMARY KEY,
                version_id BIGINT NOT NULL
                    REFERENCES fiscal_engine_rule_version(id) ON DELETE CASCADE,
                campo TEXT NOT NULL,
                operador TEXT NOT NULL DEFAULT 'igual'
                    CHECK (operador IN ('igual', 'prefixo')),
                valor TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fiscal_engine_rule_result (
                version_id BIGINT PRIMARY KEY
                    REFERENCES fiscal_engine_rule_version(id) ON DELETE CASCADE,
                cfop TEXT NOT NULL DEFAULT '',
                cst_icms TEXT NOT NULL DEFAULT '',
                csosn TEXT NOT NULL DEFAULT '',
                cst_pis TEXT NOT NULL DEFAULT '',
                cst_cofins TEXT NOT NULL DEFAULT '',
                modalidade_st TEXT NOT NULL DEFAULT '',
                aliquota_icms NUMERIC(9,4) NOT NULL DEFAULT 0,
                mva NUMERIC(9,4) NOT NULL DEFAULT 0,
                base_reducao NUMERIC(9,4) NOT NULL DEFAULT 0,
                aliquota_icms_st NUMERIC(9,4) NOT NULL DEFAULT 0,
                aliquota_pis NUMERIC(9,4) NOT NULL DEFAULT 0,
                aliquota_cofins NUMERIC(9,4) NOT NULL DEFAULT 0
            )
            """
        )
        _backfill(conn)
    finally:
        conn.autocommit = autocommit


def _backfill(conn) -> None:
    """Espelha o legado como PUBLISHED v1 — idempotente (NOT EXISTS por code)."""
    # Regra (cabeçalho)
    conn.execute(
        """
        INSERT INTO fiscal_engine_rule (code, nome, tipo, prioridade, estado)
        SELECT 'legado-' || r.id, r.nome, COALESCE(NULLIF(r.dimensao,''), 'geral'),
               r.prioridade, 'PUBLISHED'
        FROM fiscal_regra r
        WHERE r.ativo = 1
          AND NOT EXISTS (
            SELECT 1 FROM fiscal_engine_rule e WHERE e.code = 'legado-' || r.id
          )
        """
    )
    # Versão v1 (vigência da versão 'ativa' do legado quando existir)
    conn.execute(
        """
        INSERT INTO fiscal_engine_rule_version
            (rule_id, version, valid_from, valid_to, legal_reference)
        SELECT e.id, 1,
               COALESCE(v.data_inicio::date, CURRENT_DATE),
               v.data_fim::date,
               COALESCE(NULLIF(r.observacao, ''), 'backfill do legado')
        FROM fiscal_regra r
        JOIN fiscal_engine_rule e ON e.code = 'legado-' || r.id
        LEFT JOIN LATERAL (
            SELECT data_inicio, data_fim FROM fiscal_regra_versao rv
            WHERE rv.regra_id = r.id AND rv.status = 'ativa'
            ORDER BY data_inicio DESC LIMIT 1
        ) v ON TRUE
        WHERE r.ativo = 1
          AND NOT EXISTS (
            SELECT 1 FROM fiscal_engine_rule_version ev WHERE ev.rule_id = e.id
          )
        """
    )
    # Condições (critérios não vazios; ncm_prefixo vira operador prefixo)
    conn.execute(
        """
        INSERT INTO fiscal_engine_rule_condition (version_id, campo, operador, valor)
        SELECT ev.id, c.campo, c.operador, c.valor
        FROM fiscal_regra r
        JOIN fiscal_engine_rule e ON e.code = 'legado-' || r.id
        JOIN fiscal_engine_rule_version ev ON ev.rule_id = e.id AND ev.version = 1
        CROSS JOIN LATERAL (VALUES
            ('regime',           'igual',   r.regime),
            ('uf_origin',        'igual',   r.uf_origem),
            ('uf_destination',   'igual',   r.uf_destino),
            ('customer_type',    'igual',   r.tipo_cliente),
            ('customer_taxpayer_status', 'igual', r.contribuinte),
            ('merchandise_purpose', 'igual', r.finalidade),
            ('document_model',   'igual',   r.modelo_documento),
            ('operation_type',   'igual',   r.natureza_operacao),
            ('cest',             'igual',   r.cest),
            ('merchandise_origin', 'igual', r.origem),
            ('ncm',              'prefixo', r.ncm_prefixo)
        ) AS c(campo, operador, valor)
        WHERE r.ativo = 1
          AND COALESCE(c.valor, '') <> ''
          AND NOT EXISTS (
            SELECT 1 FROM fiscal_engine_rule_condition ec
            WHERE ec.version_id = ev.id AND ec.campo = c.campo
          )
        """
    )
    # Resultado prescrito (rates legados DOUBLE -> NUMERIC)
    conn.execute(
        """
        INSERT INTO fiscal_engine_rule_result (
            version_id, cfop, cst_icms, csosn, cst_pis, cst_cofins,
            modalidade_st, aliquota_icms, mva, base_reducao,
            aliquota_icms_st, aliquota_pis, aliquota_cofins
        )
        SELECT ev.id, r.cfop, r.cst_icms, r.csosn, r.cst_pis, r.cst_cofins,
               r.modalidade_st,
               COALESCE(r.aliquota_icms,0), COALESCE(r.mva,0),
               COALESCE(r.base_reducao,0), COALESCE(r.aliquota_icms_st,0),
               COALESCE(r.aliquota_pis,0), COALESCE(r.aliquota_cofins,0)
        FROM fiscal_regra r
        JOIN fiscal_engine_rule e ON e.code = 'legado-' || r.id
        JOIN fiscal_engine_rule_version ev ON ev.rule_id = e.id AND ev.version = 1
        WHERE r.ativo = 1
          AND NOT EXISTS (
            SELECT 1 FROM fiscal_engine_rule_result er WHERE er.version_id = ev.id
          )
        """
    )


def backward(conn) -> None:
    autocommit = conn.autocommit
    conn.autocommit = True
    try:
        for tabela in (
            "fiscal_engine_rule_result",
            "fiscal_engine_rule_condition",
            "fiscal_engine_rule_version",
            "fiscal_engine_rule",
        ):
            conn.execute(f"DROP TABLE IF EXISTS {tabela}")
    finally:
        conn.autocommit = autocommit
