"""Regressões do padrão curto de SKU para o cadastro do ERP."""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.repositories.produtos import ProdutoRepository
from catalog_server.services import sku_service


repo = ProdutoRepository()


def test_gerar_compacto_nao_carrega_atributos_na_chave():
    assert sku_service.gerar_compacto("ELE", "CAB", "001") == "ELE-CAB-001"
    assert sku_service.gerar_compacto(
        "ELE", "CAB", "001", produto_id=10, variacao=2
    ) == "ELE-CAB-001-02"


def test_gerar_compacto_normaliza_taxonomia_e_mantem_codigo_curto():
    sku = sku_service.gerar_compacto("Elétrico", "Cabos flexíveis", "001")
    assert sku == "ELET-CABO-001"
    assert len(sku) <= 20


def test_cadastro_de_duas_variacoes_compartilha_nucleo_do_sku(system_db):
    with system_conn() as conn:
        grupo = conn.execute(
            "INSERT INTO grupos (codigo, nome) VALUES ('ELE', 'Elétrico') RETURNING id"
        ).fetchone()["id"]
        subgrupo = conn.execute(
            "INSERT INTO subgrupos (grupo_id, codigo, nome) VALUES (?, 'CAB', 'Cabos') RETURNING id",
            (grupo,),
        ).fetchone()["id"]

    familia = repo.create_familia(
        "Cabos flexíveis",
        "",
        [{"nome": "Bitola", "tipo": "lista", "opcoes": ["2,5mm", "4mm"]}],
    )
    base = {
        "sku": "",
        "preco": 10,
        "bitola": "2,5mm",
    }
    primeiro = repo.create_product(
        familia, "Cabo flexível", "Corfio", "", "", grupo_id=grupo,
        subgrupo_id=subgrupo, dados=base, atributos={"Bitola": "2,5mm"},
    )
    segundo = repo.create_product(
        familia, "Cabo flexível", "Corfio", "", "", grupo_id=grupo,
        subgrupo_id=subgrupo, dados={**base, "bitola": "4mm"},
        atributos={"Bitola": "4mm"},
    )

    assert repo.get_product(primeiro)["sku"] == "ELE-CAB-001"
    assert repo.get_product(segundo)["sku"] == "ELE-CAB-001-02"


def test_sku_informado_manualmente_continua_valido_e_estavel(system_db):
    produto = repo.create_product(
        None, "Disjuntor", "S", "", "",
        dados={"sku": "DISJ-001", "preco": 20},
    )
    assert repo.get_product(produto)["sku"] == "DISJ-001"
