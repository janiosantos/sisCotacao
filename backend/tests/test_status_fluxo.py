"""Lifecycle orçamento→pedido (v2.18.0): transições, edição, reabrir."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.db import system_conn
from catalog_server.app_factory import create_app
from catalog_server.orcamento_status import (
    STATUS_LIST,
    aplicar_transicao,
    obter_transicoes,
    pode_editar_conteudo,
    transicao_valida,
)


def _criar_usuario(login: str, autoriza: bool = False) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, autoriza_desconto)"
            " VALUES (%s,%s,%s,%s)",
            ("Teste", login, generate_password_hash("x123"), 1 if autoriza else 0),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM perfis WHERE nome=%s", (nome,)
        ).fetchone()["id"])


def _vincular(usuario_id: int, nome_perfil: str) -> None:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s)"
            " ON CONFLICT DO NOTHING",
            (usuario_id, _perfil_id(nome_perfil)),
        )
        conn.commit()
    permissao.invalidar(usuario_id)


def _token(usuario_id: int, login: str) -> dict:
    return {"Authorization": f"Bearer {auth_token.criar_token({'id': usuario_id, 'login': login})}"}


def _novo_orcamento(c, header, cliente="CONSUMIDOR"):
    r = c.post("/api/orcamentos", headers=header, json={
        "cliente": cliente,
        "itens": [{"produto_id": 1, "nome": "P", "quantidade": 1, "preco_unitario": 10.0}],
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def test_status_list_completo():
    assert "rascunho" in STATUS_LIST
    assert "liberado" in STATUS_LIST
    assert "finalizado" in STATUS_LIST
    assert "recebido" in STATUS_LIST
    assert "cancelado" in STATUS_LIST
    assert "devolvido" in STATUS_LIST
    assert "faturado" not in STATUS_LIST


def test_transicoes_validas():
    assert transicao_valida("rascunho", "liberado")
    assert transicao_valida("rascunho", "finalizado")  # finalização direta do PDV
    assert transicao_valida("liberado", "finalizado")
    assert transicao_valida("finalizado", "recebido")
    assert transicao_valida("finalizado", "cancelado")
    assert transicao_valida("finalizado", "liberado")  # reabrir
    assert transicao_valida("recebido", "devolvido")
    assert not transicao_valida("cancelado", "finalizado")
    assert not transicao_valida("recebido", "liberado")


def test_editabilidade():
    assert pode_editar_conteudo("rascunho")
    assert pode_editar_conteudo("liberado")
    assert not pode_editar_conteudo("finalizado")
    assert not pode_editar_conteudo("recebido")


def test_finalizar_converte_pedido(system_db):
    c = create_app().test_client()
    uid = _criar_usuario("vendef")
    _vincular(uid, "Vendedor")
    h = _token(uid, "vendef")
    oid = _novo_orcamento(c, h)
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT status, virou_pedido FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "finalizado"
    assert st["virou_pedido"] == 1


def test_editar_bloqueada_apos_finalizado(system_db):
    c = create_app().test_client()
    uid = _criar_usuario("vende2")
    _vincular(uid, "Vendedor")
    h = _token(uid, "vende2")
    oid = _novo_orcamento(c, h)
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    # Editar conteúdo após finalizado → 403
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"cliente": "Outro"})
    assert r.status_code == 403
    # Trocar itens também bloqueia
    r = c.put(f"/api/orcamentos/{oid}/itens", headers=h, json={
        "itens": [{"produto_id": 2, "nome": "Q", "quantidade": 2, "preco_unitario": 5.0}],
    })
    assert r.status_code == 403


def test_transicao_invalida_rejeitada(system_db):
    c = create_app().test_client()
    uid = _criar_usuario("vende3")
    _vincular(uid, "Vendedor")
    h = _token(uid, "vende3")
    oid = _novo_orcamento(c, h)
    # cancelado → finalizado é inválida
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "cancelado"})
    r = c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    assert r.status_code == 400
    assert "inválida" in r.get_json()["error"]


def test_reabrir_finalizado_volta_liberado(system_db):
    c = create_app().test_client()
    uid = _criar_usuario("vende4", autoriza=True)
    _vincular(uid, "Operador")
    h = _token(uid, "vende4")
    oid = _novo_orcamento(c, h)
    c.patch(f"/api/orcamentos/{oid}", headers=h, json={"status": "finalizado"})
    r = c.post(f"/api/orcamentos/{oid}/reabrir", headers=h)
    assert r.status_code == 200, r.get_json()
    with system_conn() as conn:
        st = conn.execute("SELECT status, virou_pedido FROM orcamentos WHERE id=%s", (oid,)).fetchone()
    assert st["status"] == "liberado"
    assert st["virou_pedido"] == 0


def test_obter_transicoes_helper():
    destinos = set(obter_transicoes("finalizado"))
    assert "recebido" in destinos
    assert "liberado" in destinos
    assert obter_transicoes("cancelado") == []