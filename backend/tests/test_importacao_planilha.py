"""Importação de lista de produtos por planilha CSV/XLSX."""
from __future__ import annotations

import io

import pytest

from catalog_server import auth_token, permissao
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn
from catalog_server.services import importacao_planilha


def _csv(linhas: list[str]) -> bytes:
    return "\n".join(linhas).encode("utf-8")


def _busca(nome: str, marca: str = "") -> dict | None:
    with system_conn() as conn:
        r = conn.execute(
            "SELECT id, grupo_id, subgrupo_id, categoria_id, subcategoria_id, familia_id,"
            " status_cadastro, ativo FROM produtos_cadastro"
            " WHERE LOWER(nome)=LOWER(%s) AND LOWER(COALESCE(marca,''))=LOWER(%s)",
            (nome, marca),
        ).fetchone()
        return dict(r) if r else None


def test_ler_csv_cabecalho_descreve(system_db):
    conteudo = _csv([
        "DESCRICAO;MARCA;GRUPO;SUBGRUPO;CATEGORIA;SUBCATEGORIA;FAMILIA",
        "Cabo Flexível 2,5mm;Corfio;Cabos;Flexível;Eletrico;Cabo;Família Cabo",
        "Parafuso 4x20;Wetzel;Fixacao;Parafusos;Metais;Parafuso;Família Parafuso",
    ])
    linhas = importacao_planilha.ler_planilha(conteudo, "a.csv")
    assert len(linhas) == 2
    assert linhas[0]["descricao"] == "Cabo Flexível 2,5mm"
    assert linhas[0]["grupo"] == "Cabos"
    assert linhas[1]["familia"] == "Família Parafuso"


def test_ler_csv_virgula_como_delimitador(system_db):
    conteudo = _csv([
        "DESCRICAO,MARCA",
        "Conector 10mm,Famastil",
    ])
    linhas = importacao_planilha.ler_planilha(conteudo, "b.csv")
    assert linhas[0]["descricao"] == "Conector 10mm"
    assert linhas[0]["marca"] == "Famastil"


def test_ler_csv_aceita_nome_e_fallback_quando_descricao_vazia(system_db):
    descricao_acentuada = _csv([
        "DESCRIÇÃO;MARCA",
        "Lâmpada bulbo 9W;Elgin",
    ])
    linhas = importacao_planilha.ler_planilha(descricao_acentuada, "descricao-acentuada.csv")
    assert linhas[0]["descricao"] == "Lâmpada bulbo 9W"

    somente_nome = _csv([
        "NOME;MARCA",
        "Disjuntor DIN 20A;Steck",
    ])
    linhas = importacao_planilha.ler_planilha(somente_nome, "nome.csv")
    assert linhas[0]["descricao"] == "Disjuntor DIN 20A"

    ambas = _csv([
        "DESCRIÇÃO;NOME;MARCA",
        ";Tomada 20A;Tramontina",
    ])
    linhas = importacao_planilha.ler_planilha(ambas, "fallback.csv")
    assert linhas[0]["descricao"] == "Tomada 20A"

    somente_produto = _csv([
        "PRODUTO;MARCA",
        "Registro de esfera 1/2;Deca",
    ])
    linhas = importacao_planilha.ler_planilha(somente_produto, "produto.csv")
    assert linhas[0]["descricao"] == "Registro de esfera 1/2"


def test_ler_planilha_ignora_linhas_totalmente_vazias(system_db):
    conteudo = _csv([
        "DESCRICAO;MARCA;GRUPO",
        "Produto preenchido;Marca A;Elétricos",
        ";;",
    ])

    linhas = importacao_planilha.ler_planilha(conteudo, "vazias.csv")

    assert len(linhas) == 1
    assert linhas[0]["descricao"] == "Produto preenchido"


def test_importar_csv_cria_rascunho_com_taxonomia(system_db):
    conteudo = _csv([
        "DESCRICAO;MARCA;GRUPO;SUBGRUPO;CATEGORIA;SUBCATEGORIA;FAMILIA",
        "Conector 10mm;Famastil;Eletricos;Conectores;Materiais;Conector;Família Conector",
    ])
    r = importacao_planilha.importar(conteudo, "c.csv", None)
    assert r["criados"] == 1
    assert r["erros"] == 0
    p = _busca("Conector 10mm", "Famastil")
    assert p and p["status_cadastro"] == "rascunho"
    assert p["ativo"] == 0
    with system_conn() as conn:
        g = conn.execute("SELECT id FROM grupos WHERE nome='Eletricos'").fetchone()
        s = conn.execute("SELECT id FROM subgrupos WHERE nome='Conectores'").fetchone()
        c = conn.execute("SELECT id FROM categorias WHERE nome='Materiais'").fetchone()
        f = conn.execute("SELECT id FROM familias WHERE nome='Família Conector'").fetchone()
    assert g and s and c and f
    assert p["grupo_id"] == g["id"]
    assert p["subgrupo_id"] == s["id"]
    assert p["categoria_id"] == c["id"]
    assert p["familia_id"] == f["id"]


def test_importar_resolve_colisoes_de_codigo_de_grupo_e_subgrupo(system_db):
    conteudo = _csv([
        "DESCRICAO;MARCA;GRUPO;SUBGRUPO",
        "Produto Colisao A;Marca X;Taxonomia Colisao Alpha;Ferramentas Manuais",
        "Produto Colisao B;Marca X;Taxonomia Colisao Alpha;Ferramentas Mecanicas",
        "Produto Colisao C;Marca X;Taxonomia Colisao Beta;Ferramentas Manuais",
    ])

    resultado = importacao_planilha.importar(conteudo, "colisoes.csv", None)

    assert resultado["criados"] == 3
    assert resultado["erros"] == 0
    with system_conn() as conn:
        grupos = conn.execute(
            "SELECT nome, codigo FROM grupos"
            " WHERE nome IN ('Taxonomia Colisao Alpha', 'Taxonomia Colisao Beta')"
            " ORDER BY nome"
        ).fetchall()
        subgrupos = conn.execute(
            "SELECT s.nome, s.codigo FROM subgrupos s"
            " JOIN grupos g ON g.id=s.grupo_id"
            " WHERE g.nome='Taxonomia Colisao Alpha' ORDER BY s.nome"
        ).fetchall()

    assert [(g["nome"], g["codigo"]) for g in grupos] == [
        ("Taxonomia Colisao Alpha", "TAXONOMI"),
        ("Taxonomia Colisao Beta", "TAXONOM2"),
    ]
    assert [(s["nome"], s["codigo"]) for s in subgrupos] == [
        ("Ferramentas Manuais", "FERRAMEN"),
        ("Ferramentas Mecanicas", "FERRAME2"),
    ]


def test_importar_reutiliza_taxonomia_e_produto_sem_diferenciar_acentos(system_db):
    primeira = _csv([
        "DESCRICAO;MARCA;GRUPO;SUBGRUPO;CATEGORIA;SUBCATEGORIA;FAMILIA",
        "Lâmpada LED 9W;Elétrica Luz;Elétricos;Iluminação;Materiais Elétricos;Lâmpadas;Iluminação LED",
        "Refletor LED 50W;Eletrica Luz;Eletricos;Iluminacao;Materiais Eletricos;Lampadas;Iluminacao LED",
    ])
    resultado = importacao_planilha.importar(primeira, "acentos.csv", None)

    assert resultado["criados"] == 2
    with system_conn() as conn:
        assert conn.execute(
            "SELECT COUNT(*) AS total FROM grupos"
            " WHERE f_unaccent(LOWER(nome))='eletricos'"
        ).fetchone()["total"] == 1
        assert conn.execute(
            "SELECT COUNT(*) AS total FROM categorias"
            " WHERE f_unaccent(LOWER(nome))='materiais eletricos'"
        ).fetchone()["total"] == 1
        assert conn.execute(
            "SELECT COUNT(*) AS total FROM marcas"
            " WHERE f_unaccent(LOWER(nome))='eletrica luz'"
        ).fetchone()["total"] == 1

    duplicado = _csv([
        "DESCRICAO;MARCA",
        "Lampada LED 9W;Eletrica Luz",
    ])
    resultado_duplicado = importacao_planilha.importar(duplicado, "duplicado-sem-acento.csv", None)
    assert resultado_duplicado["criados"] == 0
    assert resultado_duplicado["atualizados"] == 1


def test_importar_isola_rejeicoes_e_gera_planilha_para_reimportacao(system_db):
    conteudo = _csv([
        "DESCRICAO;MARCA;GRUPO;SUBGRUPO;CATEGORIA;SUBCATEGORIA;FAMILIA",
        "Produto Válido A;Marca A;Ferragens;Fixação;Ferragens;Parafusos;Parafusos",
        ";Marca B;Ferragens;Fixação;Ferragens;Parafusos;Parafusos",
        "Produto Sem Grupo;Marca C;;Conexões;Hidráulica;Conexões;Conexões",
        "Produto Válido B;Marca D;Hidráulica;Conexões;Hidráulica;Conexões;Conexões",
    ])

    resultado = importacao_planilha.importar(conteudo, "parcial.csv", None)

    assert resultado["criados"] == 2
    assert resultado["erros"] == 2
    assert resultado["relatorio_erros_url"].endswith("/erros.xlsx")
    assert {erro["linha"] for erro in resultado["erros_detalhe"]} == {3, 4}
    assert all(erro["sugestao"] for erro in resultado["erros_detalhe"])

    relatorio = importacao_planilha.gerar_planilha_erros(resultado["importacao_id"])
    assert relatorio is not None
    conteudo_xlsx, nome = relatorio
    assert nome.endswith(".xlsx")
    assert conteudo_xlsx[:2] == b"PK"

    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.load_workbook(io.BytesIO(conteudo_xlsx), data_only=True)
    sheet = workbook["Nao importados"]
    assert [cell.value for cell in sheet[1]][:3] == ["DESCRICAO", "MARCA", "GRUPO"]
    assert sheet.max_row == 3
    assert sheet["A2"].value is None
    assert sheet["I2"].value == "DESCRIÇÃO, DESCRICAO, NOME ou PRODUTO é obrigatório."
    assert sheet["J2"].value


def test_api_importacao_parcial_disponibiliza_download_autenticado(system_db):
    with system_conn() as conn:
        usuario_id = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (?,?,?)",
            ("Administrador Importação", "admin-importacao", "x"),
        ).lastrowid
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id)"
            " SELECT ?, id FROM perfis WHERE nome='Administrador'",
            (usuario_id,),
        )
    permissao.invalidar(usuario_id)
    token = auth_token.criar_token({"id": usuario_id, "login": "admin-importacao"})
    headers = {"Authorization": f"Bearer {token}"}
    client = create_app().test_client()
    conteudo = _csv([
        "PRODUTO;MARCA",
        "Produto API Válido;Marca A",
        ";Marca B",
    ])

    response = client.post(
        "/api/produtos-cadastro/importar-planilha",
        data={"file": (io.BytesIO(conteudo), "api-parcial.csv")},
        headers=headers,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201, response.get_json()
    resultado = response.get_json()
    assert resultado["criados"] == 1
    assert resultado["erros"] == 1
    download = client.get(resultado["relatorio_erros_url"], headers=headers)
    assert download.status_code == 200
    assert download.data[:2] == b"PK"
    assert "produtos-nao-importados" in download.headers["Content-Disposition"]


def test_importar_dedup_nome_marca(system_db):
    conteudo = _csv([
        "DESCRICAO;MARCA",
        "Abraçadeira 20;Marca A",
        "Abraçadeira 20;Marca A",
    ])
    r = importacao_planilha.importar(conteudo, "d.csv", None)
    assert r["criados"] == 1
    assert r["atualizados"] == 1


def test_importar_sem_descricao_conta_erro(system_db):
    conteudo = _csv([
        "DESCRICAO;MARCA",
        ";Marca",
        "Item Valido;Marca",
    ])
    r = importacao_planilha.importar(conteudo, "e.csv", None)
    assert r["erros"] == 1
    assert r["criados"] == 1


def test_cabecalho_sem_descricao_erro(system_db):
    conteudo = _csv(["MARCA;GRUPO", "A;B"])
    try:
        importacao_planilha.importar(conteudo, "f.csv", None)
        assert False, "deveria falhar sem DESCRICAO"
    except ValueError:
        pass


def test_xlsx_importa(system_db):
    openpyxl = pytest.importorskip("openpyxl")  # dependência opcional (imagem sem o pacote)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["DESCRICAO", "MARCA", "GRUPO", "SUBGRUPO", "CATEGORIA", "SUBCATEGORIA", "FAMILIA"])
    ws.append(["Cabo 4mm", "Sil", "Cabos", "Flexíveis", "Elétrico", "Cabo", "Família Cabo"])
    buf = io.BytesIO()
    wb.save(buf)
    r = importacao_planilha.importar(buf.getvalue(), "g.xlsx", None)
    assert r["criados"] == 1
    p = _busca("Cabo 4mm", "Sil")
    assert p and p["grupo_id"] is not None and p["familia_id"] is not None


def test_importar_idempotente_mesmo_conteudo(system_db):
    conteudo = _csv(["DESCRICAO;MARCA", "Tubo 50mm;Marca X"])
    r1 = importacao_planilha.importar(conteudo, "h.csv", None)
    r2 = importacao_planilha.importar(conteudo, "h2.csv", None)
    assert r1["criados"] == 1
    assert r1["duplicado"] is False
    assert r2["duplicado"] is True
    assert r2["importacao_id"] == r1["importacao_id"]
    assert r2["criados"] == 1  # devolve o resultado original sem reprocessar
