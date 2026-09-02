"""Contratos dos relatorios analiticos de operacao."""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import relatorios_operacionais as relatorios


def test_relatorios_analiticos_vazios_mantem_contrato(system_db):
    vendas = relatorios.vendas_analitico({"data_inicio": "2026-01-01", "data_fim": "2026-12-31"})
    compras = relatorios.compras_analitico({"data_inicio": "2026-01-01", "data_fim": "2026-12-31"})
    estoque = relatorios.estoque_analitico({"limit": 10})

    assert vendas["report_key"] == "vendas.analitico"
    assert vendas["resumo"]["pedidos"] == 0
    assert compras["report_key"] == "compras.analitico"
    assert compras["resumo"]["pedidos"] == 0
    assert estoque["report_key"] == "estoque.analitico"
    assert estoque["paginacao"]["limit"] == 10


def test_relatorio_vendas_rejeita_sql_e_paginacao_invalida(system_db):
    try:
        relatorios.vendas_analitico({"agrupamento": "sql"})
        assert False, "agrupamento livre nao deveria ser aceito"
    except relatorios.RelatorioOperacionalError:
        pass


def test_resumo_vendas_nao_duplica_pedido_ou_cliente_por_produto(system_db):
    with system_conn() as conn:
        cliente = conn.execute(
            "INSERT INTO clientes (nome, tipo_pessoa) VALUES (%s,%s) RETURNING id",
            ("Cliente relatorio", "f"),
        ).fetchone()["id"]
        p1 = conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,1,%s,10) RETURNING id",
            ("Produto 1", "R-1"),
        ).fetchone()["id"]
        p2 = conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,1,%s,10) RETURNING id",
            ("Produto 2", "R-2"),
        ).fetchone()["id"]
        pedido = conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, criado_em) VALUES (%s,%s,'finalizado',%s) RETURNING id",
            (cliente, "REL-1", "2026-09-01 10:00:00"),
        ).fetchone()["id"]
        for produto in (p1, p2):
            conn.execute(
                "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, quantidade, preco_unitario, subtotal) VALUES (%s,%s,%s,1,10,10)",
                (pedido, produto, f"Produto {produto}"),
            )
        conn.commit()
    result = relatorios.vendas_analitico({"data_inicio": "2026-09-01", "data_fim": "2026-09-01", "agrupamento": "produto"})
    assert result["resumo"]["pedidos"] == 1
    assert result["resumo"]["clientes"] == 1
    try:
        relatorios.estoque_analitico({"limit": 201})
        assert False, "limite acima do teto nao deveria ser aceito"
    except relatorios.RelatorioOperacionalError:
        pass
