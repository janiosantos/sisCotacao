"""Motor fiscal v2: resolução versionada, conflitos, vigência e flag de integração.

Testes HERMÉTICOS: cada regra semeada é removida no teardown para não vazar
para os demais testes da suíte (o conftest não trunca entre testes).
"""
from __future__ import annotations

import time
import uuid
from decimal import Decimal

import pytest

from catalog_server import flags as app_flags
from catalog_server.db import system_conn
from catalog_server.fiscal import FiscalContext, EstadoFiscal
from catalog_server.fiscal.resolvedor import resolver_v2


@pytest.fixture()
def regras_limpas():
    """Teardown: remove tudo semeado pelos testes deste módulo."""
    criadas: list[int] = []
    yield criadas
    if not criadas:
        return
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
        conn.execute(f"DELETE FROM fiscal_engine_rule_version WHERE rule_id IN ({ids})")
        conn.execute(f"DELETE FROM fiscal_engine_rule WHERE id IN ({ids})")
        conn.commit()


def _seed_regra(
    criadas: list[int],
    *,
    prioridade: int = 100,
    cfop: str = "5102",
    csosn: str = "102",
    estado: str = "PUBLISHED",
    valid_from: str = "2026-01-01",
    valid_to: str | None = None,
    condicoes: dict[str, str] | None = None,
    aliquota_icms: str = "18.0000",
) -> int:
    sufixo = uuid.uuid4().hex[:8]
    with system_conn() as conn:
        rid = conn.execute(
            "INSERT INTO fiscal_engine_rule (code, nome, tipo, prioridade, estado)"
            " VALUES (?, ?, 'operacao', ?, ?)",
            (f"teste-{sufixo}", f"Regra teste {sufixo}", prioridade, estado),
        ).lastrowid
        vid = conn.execute(
            "INSERT INTO fiscal_engine_rule_version"
            " (rule_id, version, valid_from, valid_to, legal_reference)"
            " VALUES (?, 1, ?, ?, 'fonte de teste')",
            (rid, valid_from, valid_to),
        ).lastrowid
        for campo, valor in (condicoes or {"uf_origin": "MG"}).items():
            operador = "prefixo" if campo == "ncm" else "igual"
            conn.execute(
                "INSERT INTO fiscal_engine_rule_condition"
                " (version_id, campo, operador, valor) VALUES (?,?,?,?)",
                (vid, campo, operador, valor),
            )
        conn.execute(
            "INSERT INTO fiscal_engine_rule_result"
            " (version_id, cfop, csosn, aliquota_icms) VALUES (?,?,?,?)",
            (vid, cfop, csosn, aliquota_icms),
        )
        conn.commit()
    criadas.append(int(rid))
    return int(rid)


def _ctx(**over) -> FiscalContext:
    base = {
        "tax_regime": "simples_nacional",
        "uf_origin": "MG",
        "operation_date": "2026-08-22",
    }
    base.update(over)
    return FiscalContext.de_dict(base)


def test_match_unico_calculado(regras_limpas):
    _seed_regra(regras_limpas, condicoes={"uf_origin": "MG"})
    r = resolver_v2(_ctx())
    assert r.status is EstadoFiscal.CALCULATED
    assert r.cfop == "5102" and r.csosn == "102"
    assert r.icms_rate == Decimal("18.0000")
    assert r.rule_id > 0 and r.legal_reference == "fonte de teste"
    assert not r.bloqueia_emissao()


def test_sem_match_rule_not_found(regras_limpas):
    _seed_regra(regras_limpas, condicoes={"uf_origin": "SP"})
    r = resolver_v2(_ctx(uf_origin="MG"))
    assert r.status is EstadoFiscal.RULE_NOT_FOUND
    assert r.bloqueia_emissao()


def test_conflito_mesma_prioridade(regras_limpas):
    _seed_regra(regras_limpas, cfop="5102", csosn="102", prioridade=500)
    _seed_regra(regras_limpas, cfop="5405", csosn="500", prioridade=500)
    r = resolver_v2(_ctx())
    assert r.status is EstadoFiscal.FISCAL_RULE_CONFLICT
    assert "#" in "".join(r.errors)


def test_prioridade_menor_especifica_vence(regras_limpas):
    _seed_regra(regras_limpas, cfop="5405", csosn="500", prioridade=900,
                condicoes={"uf_origin": "MG", "customer_type": "consumidor"})
    _seed_regra(regras_limpas, cfop="5102", csosn="102", prioridade=500)
    r = resolver_v2(_ctx(customer_type="consumidor"))
    assert r.status is EstadoFiscal.CALCULATED
    assert r.cfop == "5102"


def test_vigencia_fora_rule_not_found(regras_limpas):
    _seed_regra(regras_limpas, valid_from="2030-01-01")
    r = resolver_v2(_ctx(operation_date="2026-08-22"))
    assert r.status is EstadoFiscal.RULE_NOT_FOUND


def test_data_da_operacao_seleciona_vigencia(regras_limpas):
    _seed_regra(regras_limpas, valid_from="2026-01-01", valid_to="2026-06-30", cfop="5102")
    _seed_regra(regras_limpas, valid_from="2026-07-01", cfop="6108", csosn="102")
    r_junho = resolver_v2(_ctx(operation_date="2026-06-15"))
    r_agosto = resolver_v2(_ctx(operation_date="2026-08-15"))
    assert r_junho.cfop == "5102"
    assert r_agosto.cfop == "6108"


def test_condicao_prefixo_ncm(regras_limpas):
    _seed_regra(regras_limpas, prioridade=100, condicoes={"ncm": "8544"}, cfop="5102")
    _seed_regra(regras_limpas, prioridade=500, cfop="5109", csosn="102")
    r_cabo = resolver_v2(_ctx(ncm="8544.42.00"))
    r_outro = resolver_v2(_ctx(ncm="7419.80.00"))
    assert r_cabo.cfop == "5102"
    assert r_outro.cfop == "5109"


@pytest.fixture()
def engine_flag_on(monkeypatch):
    """Liga FISCAL_ENGINE_V2 via cache forçado (sem tocar no banco)."""
    monkeypatch.setattr(app_flags, "_cache", {"FISCAL_ENGINE_V2": True})
    monkeypatch.setattr(app_flags, "_cache_em", time.monotonic())


@pytest.fixture()
def ambiente_integracao():
    """Produto+variante+fiscal_config+emitente mínimos, limpos no teardown."""
    sufixo = uuid.uuid4().hex[:8]
    criados: dict[str, int] = {}
    with system_conn() as conn:
        pid = conn.execute(
            "INSERT INTO produtos_cadastro (nome) VALUES ('PROD MOTOR V2')"
        ).lastrowid
        vid = conn.execute(
            "INSERT INTO variantes (produto_id, sku) VALUES (?, ?)",
            (pid, f"MOTORV2-{sufixo}"),
        ).lastrowid
        conn.execute(
            "INSERT INTO fiscal_config (variante_id, aliquota_icms) VALUES (?, 18)",
            (vid,),
        )
        eid = conn.execute(
            "INSERT INTO emitente (razao_social, cnpj, ativo, regime_tributario, uf)"
            " VALUES ('EMITENTE TESTE CI', '00000000000191', 1,"
            " 'simples_nacional', 'MG')"
        ).lastrowid
        conn.commit()
        criados = {"produto": int(pid), "variante": int(vid), "emitente": int(eid)}
    yield criados
    with system_conn() as conn:
        conn.execute("DELETE FROM fiscal_config WHERE variante_id=?", (criados["variante"],))
        conn.execute("DELETE FROM variantes WHERE id=?", (criados["variante"],))
        conn.execute("DELETE FROM produtos_cadastro WHERE id=?", (criados["produto"],))
        conn.execute("DELETE FROM emitente WHERE id=?", (criados["emitente"],))
        conn.commit()


def test_integracao_engine_usa_cfop_v2(engine_flag_on, ambiente_integracao):
    from catalog_server.services import fiscal_engine

    criados = ambiente_integracao
    regras: list[int] = []
    try:
        _seed_regra(regras, prioridade=100, cfop="5405", csosn="500",
                    condicoes={"uf_origin": "MG", "operation_type": "venda"})
        res = fiscal_engine.calculate(
            criados["variante"], operacao="venda", tipo_cliente="consumidor"
        )
        assert res is not None
        assert res["cfop_origem"] == "regra_v2"
        assert res["cfop"] == "5405"
        assert res["motor_v2"]["status"] == "CALCULATED"
    finally:
        if regras:
            ids = ", ".join(str(i) for i in regras)
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
