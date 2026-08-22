"""Golden test do dossiê 2026-08-cabos-eletricos (NCM 8544, MG, Simples)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from catalog_server import flags as app_flags
from catalog_server.db import system_conn
from catalog_server.fiscal.resolvedor import resolver_v2

_MIG = (
    Path(__file__).resolve().parent.parent
    / "migrations" / "versions" / "0071_seeds_normativas_8544.py"
)


def _helpers():
    spec = importlib.util.spec_from_file_location("seeds_0071", _MIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def seeds(limpa_engine_rules):
    m = _helpers()
    criadas: list[int] = []
    with system_conn() as conn:
        rid1 = m._regra(
            conn,
            code="norma-8544-substituido-retido",
            nome="MG · Simples · 8544 revenda substituído já retido",
            prioridade=900,
            legal="Consulta SEF/MG 105/2021 + RICMS/MG Anexo VII Cap.12 item 7.0",
            fonte="https://www.legisweb.com.br/legislacao/?id=415741",
        )
        vid1 = m._versao(conn, rid1)
        m._condicoes(conn, vid1, {
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
        conn.commit()
        criadas += [rid1]
    yield criadas
    if criadas:
        ids = ", ".join(str(i) for i in criadas)
        with system_conn() as conn:
            conn.execute(
                f"DELETE FROM fiscal_engine_rule_result WHERE version_id IN"
                f" (SELECT id FROM fiscal_engine_rule_version WHERE rule_id IN ({ids}))"
            )
            conn.execute(
                f"DELETE FROM fiscal_engine_rule_condition WHERE version_id IN"
                f" (SELECT id FROM fiscal_engine_rule_version WHERE rule_id IN ({ids}))"
            )
            conn.execute(
                f"DELETE FROM fiscal_engine_rule_version WHERE rule_id IN ({ids})"
            )
            conn.execute(f"DELETE FROM fiscal_engine_rule WHERE id IN ({ids})")
            conn.commit()


@pytest.fixture()
def limpa_engine_rules():
    """Limpa regras de engine antes/depois para hermeticidade."""
    def _limpar():
        with system_conn() as conn:
            conn.execute(
                "DELETE FROM fiscal_engine_rule_result WHERE version_id IN"
                " (SELECT id FROM fiscal_engine_rule_version"
                "  WHERE rule_id IN (SELECT id FROM fiscal_engine_rule"
                "                    WHERE code LIKE 'norma-%'))"
            )
            conn.execute(
                "DELETE FROM fiscal_engine_rule_condition WHERE version_id IN"
                " (SELECT id FROM fiscal_engine_rule_version"
                "  WHERE rule_id IN (SELECT id FROM fiscal_engine_rule"
                "                    WHERE code LIKE 'norma-%'))"
            )
            conn.execute(
                "DELETE FROM fiscal_engine_rule_version WHERE rule_id IN"
                " (SELECT id FROM fiscal_engine_rule WHERE code LIKE 'norma-%')"
            )
            conn.execute(
                "DELETE FROM fiscal_engine_rule WHERE code LIKE 'norma-%'"
            )
            conn.commit()
    _limpar()
    yield
    _limpar()


def test_golden_substituido_ja_retido(seeds):
    r = resolver_v2({
        "tax_regime": "simples_nacional",
        "uf_origin": "MG",
        "uf_destination": "MG",
        "operation_type": "venda",
        "operation_date": "2026-08-22",
        "ncm": "8544.49.00",
    })
    assert r.status.value == "CALCULATED"
    assert r.cfop == "5405"
    assert r.csosn == "500"
    assert r.rule_id == seeds[0]


def test_sem_regra_bloqueia(seeds):
    # NCM fora da família (sem match) -> RULE_NOT_FOUND, nunca zero silencioso
    r = resolver_v2({
        "tax_regime": "simples_nacional",
        "uf_origin": "MG",
        "uf_destination": "MG",
        "operation_type": "venda",
        "ncm": "7318.15.00",  # parafuso — sem regra semeada ainda
    })
    assert r.status is EstadoFiscal.RULE_NOT_FOUND


# EstadoFiscal importado após uso acima (top-level no módulo fiscal)
from catalog_server.fiscal.estados import EstadoFiscal  # noqa: E402
