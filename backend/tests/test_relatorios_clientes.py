"""Regressões dos relatórios de clientes e exportação."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import exportacao_relatorios, relatorios_clientes


def _admin() -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        uid = int(conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s) RETURNING id",
            ("Relatório", "rel-clientes", generate_password_hash("x")),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    return uid


def _dados() -> tuple[int, int]:
    with system_conn() as conn:
        cid = int(conn.execute(
            "INSERT INTO clientes (nome, tipo_pessoa, segmento, categoria, data_nascimento, cidade, uf) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            ("Eletricista Teste", "f", "profissional", "eletricista", "1985-07-20", "Belo Horizonte", "MG"),
        ).fetchone()["id"])
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco, custo_unitario) VALUES (%s,1,%s,10,5) RETURNING id",
            ("Cabo teste", "REL-1"),
        ).fetchone()["id"])
        oid = int(conn.execute(
            "INSERT INTO orcamentos (cliente_id, numero, status, cliente, total, subtotal, criado_em) "
            "VALUES (%s,%s,'finalizado',%s,20,20,%s) RETURNING id",
            (cid, "REL-1", "Eletricista Teste", "2026-07-21 10:00:00"),
        ).fetchone()["id"])
        conn.execute(
            "INSERT INTO orcamento_itens (orcamento_id, produto_id, nome, sku, quantidade, preco_unitario, subtotal) "
            "VALUES (%s,%s,%s,%s,2,10,20)",
            (oid, pid, "Cabo teste", "REL-1"),
        )
        conn.commit()
    return cid, oid


def test_clientes_filtra_segmento_e_aniversario(system_db):
    _dados()
    result = relatorios_clientes.clientes({
        "segmento": "profissional",
        "aniversario_inicio": "2026-07-01",
        "aniversario_fim": "2026-07-31",
    })
    assert result["paginacao"]["total"] == 1
    assert result["itens"][0]["data_nascimento"] == "1985-07-20"
    assert result["itens"][0]["ultima_compra"] == "2026-07-21"


def test_compras_cliente_e_exportacao(system_db):
    cid, _ = _dados()
    result = relatorios_clientes.compras_cliente(cid, {"data_inicio": "2026-07-01", "data_fim": "2026-07-31"})
    assert result["resumo"]["pedidos"] == 1
    assert result["resumo"]["receita_liquida"] == 20.0
    csv_data = exportacao_relatorios.csv_bytes("clientes.compras", result)
    assert b"Pedido" in csv_data
    xlsx_data = exportacao_relatorios.xlsx_bytes("clientes.compras", result)
    assert xlsx_data[:2] == b"PK"


def test_api_clientes_report_requires_export_permission(system_db):
    cid, _ = _dados()
    uid = _admin()
    client = create_app().test_client()
    token = auth_token.criar_token({"id": uid, "login": "rel-clientes"})
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"/api/relatorios/clientes?segmento=profissional", headers=headers)
    assert response.status_code == 200
    response = client.get(f"/api/relatorios/clientes/exportar?formato=csv", headers=headers)
    assert response.status_code == 200
    response = client.get(f"/api/relatorios/clientes/compras?cliente_id={cid}", headers=headers)
    assert response.status_code == 200
