"""Feature flags: runtime, cache, persistência e proteção de registro."""
from __future__ import annotations

import pytest

from catalog_server import flags


@pytest.fixture()
def flag_teste(monkeypatch):
    """Registra uma flag de teste isolada do registro oficial."""
    monkeypatch.setattr(flags, "REGISTRADAS", {"TESTE_X": "flag de teste"})
    flags.invalidar()
    yield "TESTE_X"
    flags.invalidar()


def test_default_false_quando_ausente(flag_teste):
    assert flags.ativa("TESTE_X") is False


def test_default_respeitado_quando_ausente(flag_teste):
    assert flags.ativa("TESTE_X", default=True) is True


def test_definir_liga_e_persiste(flag_teste):
    flags.definir("TESTE_X", True)
    flags.invalidar()
    assert flags.ativa("TESTE_X") is True
    nomes = [f["nome"] for f in flags.listar()]
    assert "TESTE_X" in nomes
    item = next(f for f in flags.listar() if f["nome"] == "TESTE_X")
    assert item["ativo"] is True
    assert item["descricao"] == "flag de teste"


def test_definir_desliga(flag_teste):
    flags.definir("TESTE_X", True)
    flags.definir("TESTE_X", False)
    flags.invalidar()
    assert flags.ativa("TESTE_X") is False


def test_flag_nao_registrada_rejeitada():
    with pytest.raises(ValueError):
        flags.definir("NAO_EXISTE", True)


def test_falha_de_banco_retorna_default(flag_teste, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(flags, "system_conn", _boom)
    monkeypatch.setattr(flags, "_cache", None)  # sem cache válido anterior
    flags.invalidar()
    assert flags.ativa("TESTE_X") is False
    assert flags.ativa("TESTE_X", default=True) is True
