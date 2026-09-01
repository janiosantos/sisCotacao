"""Entrada fiscal XML (REC-004)."""
from __future__ import annotations

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import nfe_entrada


def _xml(chave: str, cnpj: str, cProd: str, cEAN: str, desc: str, qtd: float, vun: float, serie: str = "1") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe Id="NFe{chave}">
    <ide><nNF>123</nNF><serie>{serie}</serie><dhEmi>2026-08-15T10:00:00-03:00</dhEmi></ide>
    <emit><CNPJ>{cnpj}</CNPJ></emit>
    <det nItem="1">
      <prod>
        <cProd>{cProd}</cProd>
        <cEAN>{cEAN}</cEAN>
        <xProd>{desc}</xProd>
        <NCM>85444900</NCM>
        <CFOP>2101</CFOP>
        <uCom>UN</uCom>
        <qCom>{qtd}</qCom>
        <vUnCom>{vun}</vUnCom>
      </prod>
      <imposto><ICMS><ICMS00><CST>00</CST></ICMS00></ICMS></imposto>
    </det>
  </infNFe>
</NFe>"""


def _setup(system_db) -> None:
    with system_conn() as conn:
        conn.execute("INSERT INTO fornecedores (nome, whatsapp, cnpj_cpf) VALUES (%s,%s,%s)", ("F1", "1", "12345678000190"))
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, ean, preco, unidade_venda) VALUES (%s,%s,%s,%s,%s,%s)", ("Cabo", 1, "N-1", "7891000000001", 10.0, "UN"))
        conn.commit()


def test_importar_xml_vincula_por_ean(system_db):
    _setup(system_db)
    r = nfe_entrada.importar_xml(_xml("35260812345678000190000150000001231000000001", "12345678000190", "A1", "7891000000001", "Cabo", 50.0, 8.0))
    assert r["fornecedor_id"] is not None
    assert r["itens"] == 1
    assert r["vinculados"] == 1  # EAN bateu
    det = nfe_entrada.detalhe(r["id"])
    assert det["itens"][0]["status"] == "vinculado"
    assert float(det["itens"][0]["quantidade"]) == 50.0


def test_xml_duplicado_rejeitado(system_db):
    _setup(system_db)
    chave = "35260812345678000190000150000001231000000001"
    nfe_entrada.importar_xml(_xml(chave, "12345678000190", "A1", "7891000000001", "Cabo", 10.0, 8.0))
    try:
        nfe_entrada.importar_xml(_xml(chave, "12345678000190", "A1", "7891000000001", "Cabo", 10.0, 8.0))
        assert False, "XML duplicado deveria ser rejeitado"
    except ValueError as exc:
        assert "duplicado" in str(exc)


def test_item_sem_vinculo_nao_confirma(system_db):
    _setup(system_db)
    chave = "35260812345678000190000150000001231000000002"
    r = nfe_entrada.importar_xml(_xml(chave, "12345678000190", "ZZZ", "9999999999999", "Produto desconhecido", 5.0, 2.0))
    assert r["vinculados"] == 0
    try:
        nfe_entrada.confirmar(r["id"])
        assert False, "item sem vínculo não confirma"
    except ValueError as exc:
        assert "sem vínculo" in str(exc)


def test_vincular_manual_e_confirmar(system_db):
    _setup(system_db)
    with system_conn() as conn:
        pid = int(conn.execute("SELECT id FROM produtos_cadastro WHERE sku='N-1'").fetchone()["id"])
    chave = "35260812345678000190000150000001231000000003"
    r = nfe_entrada.importar_xml(_xml(chave, "12345678000190", "ZZZ", "9999999999999", "Produto desconhecido", 5.0, 2.0))
    item = nfe_entrada.detalhe(r["id"])["itens"][0]
    nfe_entrada.vincular_item(item["id"], pid)
    r2 = nfe_entrada.confirmar(r["id"])
    assert len(r2["itens_nf"]) == 1
    assert r2["itens_nf"][0]["produto_id"] == pid


def test_xml_invalido(system_db):
    try:
        nfe_entrada.importar_xml("<not-xml>")
        assert False
    except ValueError:
        pass


def test_rejeitar(system_db):
    _setup(system_db)
    chave = "35260812345678000190000150000001231000000004"
    r = nfe_entrada.importar_xml(_xml(chave, "12345678000190", "A1", "7891000000001", "Cabo", 1.0, 8.0))
    nfe_entrada.rejeitar(r["id"], "nota errada")
    try:
        nfe_entrada.confirmar(r["id"])
        assert False
    except ValueError as exc:
        assert "rejeitada" in str(exc)


def test_api_nfe_entrada(system_db):
    _setup(system_db)
    uid = _usuario("nfe_api")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) SELECT %s, id FROM perfis WHERE nome='Administrador'",
            (uid,),
        )
        conn.commit()
    permissao.invalidar(uid)
    client = create_app().test_client()
    h = {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'nfe_api'})}"}
    chave = "35260812345678000190000150000001231000000005"
    r = client.post("/api/nfe-entrada", headers=h, json={"xml": _xml(chave, "12345678000190", "A1", "7891000000001", "Cabo", 10.0, 8.0)})
    assert r.status_code == 201, r.get_json()
    nfe_id = r.get_json()["id"]
    assert client.get("/api/nfe-entrada", headers=h).status_code == 200
    assert client.get(f"/api/nfe-entrada/{nfe_id}", headers=h).status_code == 200
    r = client.post(f"/api/nfe-entrada/{nfe_id}/confirmar", headers=h)
    assert r.status_code == 200


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