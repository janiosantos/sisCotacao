"""Testes do Sprint 1: SKUService, importação JSON e atributos JSONB+EAV."""
from __future__ import annotations

import json

import pytest
from psycopg.errors import UniqueViolation

from catalog_server.db import system_conn
from catalog_server.importar_catalogo import importar_json_conteudo
from catalog_server.services import sku_service


# ---------------------------------------------------------------------------
# SKUService
# ---------------------------------------------------------------------------

def test_normalizar():
    assert sku_service.normalizar("  ele-cab-25  ") == "ELE-CAB-25"
    assert sku_service.normalizar(None) == ""


def test_validar_aceita_charset_e_rejeita_espacos_vazios():
    ok, err = sku_service.validar("ELE-CAB/25.A_1")
    assert ok and err == ""
    ok, err = sku_service.validar("")
    assert not ok and "vazio" in err
    ok, err = sku_service.validar("ELE CAB")  # espaço interno
    assert not ok
    ok, err = sku_service.validar("A" * 70)
    assert not ok and "máximo" in err


def test_gerar_deterministico():
    assert sku_service.gerar(10, 3) == "SKU-10-3"
    assert sku_service.gerar(10, 3, base="cabo azul") == "CABO-AZUL-10-3"


def test_reservar_vazio_gera_sku(system_db):
    with system_conn() as conn:
        sku, aviso = sku_service.reservar("", produto_id=1, variante_id=5, conn=conn)
    assert sku == "SKU-1-5" and aviso


def test_reservar_duplicado_sufixa(system_db):
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, marca) VALUES ('Teste','X')"
        )
        pid = conn.execute("SELECT MAX(id) FROM produtos_cadastro").fetchone()[0]
        conn.execute(
            "INSERT INTO variantes (produto_id, sku) VALUES (?,?)", (pid, "ELE-CAB-25")
        )
        vid = conn.execute("SELECT MAX(id) FROM variantes").fetchone()[0]
        sku2, aviso2 = sku_service.reservar("ELE-CAB-25", pid, vid + 1, conn=conn)
        assert sku2 == "ELE-CAB-25-2" and "duplicado" in aviso2
        # Persiste o reservado para simular o fluxo real antes da próxima reserva.
        conn.execute(
            "INSERT INTO variantes (produto_id, sku) VALUES (?,?)",
            (pid, sku2),
        )
        sku3, aviso3 = sku_service.reservar("ELE-CAB-25", pid, vid + 2, conn=conn)
        assert sku3 == "ELE-CAB-25-3"


def test_reservar_duplicado_sem_resolver(system_db):
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, marca) VALUES ('Teste','X')"
        )
        pid = conn.execute("SELECT MAX(id) FROM produtos_cadastro").fetchone()[0]
        conn.execute(
            "INSERT INTO variantes (produto_id, sku) VALUES (?,?)", (pid, "ELE-CAB-25")
        )
        sku, aviso = sku_service.reservar(
            "ELE-CAB-25", pid, 999, conn=conn, resolver_conflito=False
        )
    assert sku == "" and "já existe" in aviso


# ---------------------------------------------------------------------------
# Importação JSON (idempotente, JSONB + EAV sincronizados)
# ---------------------------------------------------------------------------

_JSON = {
    "formato": 1,
    "produtos": [
        {
            "id": 1,
            "url": "https://loja.com/cabo-25",
            "sku": "CAB-25",
            "ean": "789123",
            "name": "Cabo Flexível 2,5mm",
            "brand": "Cobrecom",
            "category": "Fios e Cabos",
            "price": 12.5,
            "atributos": {"family": "cabo", "base": "Cabo Flexível 2,5mm", "diameter": "2,5mm", "color": "Verde"},
            "imagens": [
                {"filename": "cab-25.jpg", "url": "https://loja.com/img/cab-25.jpg"}
            ],
        },
        {
            "id": 2,
            "url": "https://loja.com/cabo-25-preto",
            "sku": "CAB-25",
            "ean": "789124",
            "name": "Cabo Flexível 2,5mm",
            "brand": "Cobrecom",
            "category": "Fios e Cabos",
            "price": 12.9,
            "atributos": {"family": "cabo", "base": "Cabo Flexível 2,5mm", "diameter": "2,5mm", "color": "Preto"},
            "imagens": [],
        },
    ],
}


def test_importacao_json_cria_grupo_e_variantes(system_db):
    res = importar_json_conteudo(json.dumps(_JSON, ensure_ascii=False))
    assert res["criados"] == 1 and res["grupos"] == 1 and res["produtos"] == 2
    with system_conn() as conn:
        nprod = conn.execute("SELECT COUNT(*) FROM produtos_cadastro").fetchone()[0]
        nvar = conn.execute("SELECT COUNT(*) FROM variantes").fetchone()[0]
        assert nprod == 1 and nvar == 2
        # SKU duplicado do crawler resolvido (segunda variante sufixada).
        skus = [r[0] for r in conn.execute("SELECT sku FROM variantes ORDER BY id")]
        assert len(set(skus)) == 2
        # EAV sincronizado.
        neav = conn.execute(
            "SELECT COUNT(*) FROM variante_atributos va"
            " JOIN variantes v ON v.id=va.variante_id WHERE v.produto_id=?",
            (nprod,),
        ).fetchone()[0]
        assert neav == 4
        # JSONB gravado.
        njson = conn.execute(
            "SELECT COUNT(*) FROM variantes WHERE atributos IS NOT NULL"
            " AND atributos <> '{}' AND produto_id=?",
            (nprod,),
        ).fetchone()[0]
        assert njson == 2


def test_importacao_json_idempotente(system_db):
    importar_json_conteudo(json.dumps(_JSON, ensure_ascii=False))
    res = importar_json_conteudo(json.dumps(_JSON, ensure_ascii=False))
    assert res["criados"] == 0 and res["atualizados"] == 1
    with system_conn() as conn:
        nprod = conn.execute("SELECT COUNT(*) FROM produtos_cadastro").fetchone()[0]
        nvar = conn.execute("SELECT COUNT(*) FROM variantes").fetchone()[0]
        assert nprod == 1 and nvar == 2


def test_importacao_remove_variante_ausente(system_db):
    importar_json_conteudo(json.dumps(_JSON, ensure_ascii=False))
    apenas_um = {"formato": 1, "produtos": [_JSON["produtos"][0]]}
    importar_json_conteudo(json.dumps(apenas_um, ensure_ascii=False))
    with system_conn() as conn:
        nvar = conn.execute("SELECT COUNT(*) FROM variantes").fetchone()[0]
        assert nvar == 1


def test_importacao_json_vazio(system_db):
    res = importar_json_conteudo("{}")
    assert res["produtos"] == 0


# ---------------------------------------------------------------------------
# Migração 0053: marcas + atributos JSONB + SKU único
# ---------------------------------------------------------------------------

def test_migracao_0053_estrutura(system_db):
    """A fixture `system_db` aplica a 0053; valida a estrutura resultante."""
    with system_conn() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables"
                " WHERE table_schema='public'"
            ).fetchall()
        }
        cols = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name='variantes'"
            ).fetchall()
        }
        assert "marcas" in tables
        assert "atributos" in cols


def test_migracao_0053_sku_unico_no_banco(system_db):
    """O índice parcial bloqueia SKU duplicado preenchido."""
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO produtos_cadastro (nome, marca) VALUES ('Teste','X')"
        )
        pid = conn.execute(
            "SELECT MAX(id) FROM produtos_cadastro"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO variantes (produto_id, sku) VALUES (?,?)", (pid, "SKU-A")
        )
        with pytest.raises(UniqueViolation):
            conn.execute(
                "INSERT INTO variantes (produto_id, sku) VALUES (?,?)", (pid, "SKU-A")
            )