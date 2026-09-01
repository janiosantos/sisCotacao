"""Comparação de propostas (COM-009): custo efetivo e decisão de vencedor com justificativa."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.repositories.compras_avancado import solicitacao_repo
from catalog_server.services import cotacao_necessidade, comparacao


def _usuario(login: str) -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Op", login, generate_password_hash("x")),
        )
        uid = int(cur.lastrowid)
        conn.commit()
    return uid


def _setup_cotacao(system_db) -> tuple[int, int, int]:
    solic = _usuario("cmp_sol")
    aprov = _usuario("cmp_apr")
    with system_conn() as conn:
        pid = int(conn.execute(
            "INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s) RETURNING id",
            ("P", 1, "CMP-1", 10.0),
        ).fetchone()["id"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F1", "1"))
        f1 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedores (nome, whatsapp) VALUES (%s,%s)", ("F2", "2"))
        f2 = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        conn.execute("INSERT INTO fornecedor_preferencial (produto_id, fornecedor_id, ranking) VALUES (%s,%s,1)", (pid, f1))
        conn.commit()
    sc = solicitacao_repo.create("SOL-CMP", usuario_id=solic)
    solicitacao_repo.add_item(sc, pid, 10)
    solicitacao_repo.transicionar(sc, "enviada", solic)
    solicitacao_repo.transicionar(sc, "aprovada", aprov)
    r = cotacao_necessidade.gerar_cotacao(sc)
    cot_id = r["cotacao_id"]
    with system_conn() as conn:
        citem = conn.execute("SELECT id FROM cotacao_itens WHERE cotacao_id=%s", (cot_id,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO cotacao_precos (cotacao_item_id, fornecedor_id, preco_unitario, desconto, disponibilidade_estoque)"
            " VALUES (%s,%s,10.0,0,1), (%s,%s,12.0,0,1)",
            (citem, f1, citem, f2),
        )
        conn.commit()
        precos = [dict(r) for r in conn.execute("SELECT id, fornecedor_id FROM cotacao_precos WHERE cotacao_item_id=%s ORDER BY id", (citem,)).fetchall()]
    return cot_id, precos[0]["id"], precos[1]["id"]


def test_custo_efetivo():
    assert comparacao.custo_efetivo(100, 18, 1.65, 7.6) > 100
    assert comparacao.custo_efetivo(100, 0, 0, 0) == 100


def test_montar_comparacao(system_db):
    cot_id, p1, p2 = _setup_cotacao(system_db)
    m = comparacao.montar_comparacao(cot_id)
    assert len(m["itens"]) == 1
    it = m["itens"][0]
    assert len(it["precos"]) == 2
    for fid, pr in it["precos"].items():
        assert "custo_efetivo" in pr
        assert pr["custo_efetivo"] >= pr["preco_liquido"]


def test_decidir_vencedor_limpa_outros(system_db):
    cot_id, p1, p2 = _setup_cotacao(system_db)
    comparacao.decidir_vencedor(p1, "melhor preço e prazo", 1)
    with system_conn() as conn:
        r1 = conn.execute("SELECT vencedor FROM cotacao_precos WHERE id=%s", (p1,)).fetchone()
        r2 = conn.execute("SELECT vencedor FROM cotacao_precos WHERE id=%s", (p2,)).fetchone()
        cot = conn.execute("SELECT decisao_concluida FROM cotacoes WHERE id=%s", (cot_id,)).fetchone()
    assert r1["vencedor"] is True
    assert r2["vencedor"] is False
    assert cot["decisao_concluida"] is True  # único item → concluído


def test_justificativa_obrigatoria(system_db):
    cot_id, p1, p2 = _setup_cotacao(system_db)
    try:
        comparacao.decidir_vencedor(p1, "")
        assert False
    except ValueError as exc:
        assert "justificativa" in str(exc)


def test_api_comparacao(system_db):
    cot_id, p1, p2 = _setup_cotacao(system_db)
    uid = _usuario("cmp_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'cmp_api'})}"}
    r = client.get(f"/api/cotacoes/{cot_id}/comparacao", headers=h)
    assert r.status_code == 200, r.get_json()
    r = client.post(f"/api/cotacoes/precos/{p1}/vencedor", headers=h, json={"justificativa": "custo total menor"})
    assert r.status_code == 200
    r = client.post(f"/api/cotacoes/precos/{p1}/vencedor", headers=h, json={"justificativa": ""})
    assert r.status_code == 400