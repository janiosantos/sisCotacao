"""Importação de lista de produtos por planilha CSV/XLSX."""
from __future__ import annotations

import io

import pytest

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
    assert r2["criados"] == 0
    assert r2["atualizados"] == 1  # dedup por nome+marca, não duplica