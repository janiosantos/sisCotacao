"""Importação de lista de produtos por planilha CSV/XLSX.

Formato esperado: 1 linha de cabeçalho com as colunas (a única obrigatória é
DESCRICAO):

    DESCRICAO | MARCA | GRUPO | SUBGRUPO | CATEGORIA | SUBCATEGORIA | FAMILIA

- Colunas em qualquer ordem/caixa; acentos e espaços são normalizados.
- GRUPO/SUBGRUPO/CATEGORIA/SUBCATEGORIA/FAMILIA/MARCA são opcionais.
- A taxonomia é resolvida por nome (create-or-get): grupo, subgrupo, categoria,
  subcategoria, família e marca.
- Produtos são criados como RASCUNHO (ativo 0) — revisar/publicar antes de vender.
- Deduplicação por nome+marca (case-insensitive); linhas já existentes são
  contadas como "atualizadas" e não duplicam.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path

from catalog_server import categorias
from catalog_server.db import system_conn
from catalog_server.repositories import marcas as marcas_repo

_CAMPOS = ("descricao", "marca", "grupo", "subgrupo", "categoria", "subcategoria", "familia")


def _normalizar_nome(s) -> str:
    """Normaliza o rótulo da coluna: sem acentos/espaços, em maiúsculas."""
    s = unicodedata.normalize("NFD", (s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s_\-]+", "", s).upper()


def _valor(s):
    if s is None:
        return ""
    return str(s).strip()


def _ler_csv(conteudo: bytes) -> list[dict]:
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = conteudo.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("Não foi possível decodificar o CSV (UTF-8/Latin-1).")

    primeira = (text.splitlines() or [""])[0]
    delim = ";" if primeira.count(";") >= primeira.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    if not reader.fieldnames:
        raise ValueError("Planilha sem cabeçalho.")
    mapa = {_normalizar_nome(h): h for h in reader.fieldnames}
    if "DESCRICAO" not in mapa:
        raise ValueError("Cabeçalho sem a coluna obrigatória DESCRICAO.")
    linhas: list[dict] = []
    for raw in reader:
        linhas.append({campo: _valor(raw.get(mapa.get(_normalizar_nome(campo), ""))) for campo in _CAMPOS})
    return linhas


def _ler_xlsx(conteudo: bytes) -> list[dict]:
    try:
        import openpyxl
    except ImportError:
        raise ValueError("openpyxl não instalado — XLSX indisponível.")
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        raise ValueError("Arquivo XLSX sem planilhas.")
    rows = ws.iter_rows(values_only=True)
    try:
        header = next(rows)
    except StopIteration:
        raise ValueError("Planilha XLSX vazia.")
    if not header:
        raise ValueError("Planilha XLSX sem cabeçalho.")
    mapa = {_normalizar_nome(h): i for i, h in enumerate(header) if h is not None}
    if "DESCRICAO" not in mapa:
        raise ValueError("Cabeçalho sem a coluna obrigatória DESCRICAO.")
    linhas: list[dict] = []
    for r in rows:
        if r is None:
            continue
        def pega(campo: str) -> str:
            idx = mapa.get(_normalizar_nome(campo))
            if idx is None or idx >= len(r):
                return ""
            return _valor(r[idx])
        linhas.append({campo: pega(campo) for campo in _CAMPOS})
    return linhas


def ler_planilha(conteudo: bytes, nome_arquivo: str) -> list[dict]:
    """Lê a planilha (CSV ou XLSX) e devolve as linhas normalizadas."""
    ext = Path(nome_arquivo or "").suffix.lower()
    if ext == ".xlsx":
        return _ler_xlsx(conteudo)
    return _ler_csv(conteudo)


def _resolver_grupo(conn, nome: str) -> int | None:
    if not nome:
        return None
    row = conn.execute(
        "SELECT id FROM grupos WHERE LOWER(nome)=LOWER(?)", (nome,)
    ).fetchone()
    if row:
        return row["id"]
    codigo = re.sub(r"[^A-Z0-9]", "", _normalizar_nome(nome))[:8] or "G"
    return conn.execute(
        "INSERT INTO grupos (codigo, nome, ativo) VALUES (?,?,1)",
        (codigo, nome),
    ).lastrowid


def _resolver_subgrupo(conn, grupo_id: int | None, nome: str) -> int | None:
    if not grupo_id or not nome:
        return None
    row = conn.execute(
        "SELECT id FROM subgrupos WHERE grupo_id=? AND LOWER(nome)=LOWER(?)",
        (grupo_id, nome),
    ).fetchone()
    if row:
        return row["id"]
    codigo = re.sub(r"[^A-Z0-9]", "", _normalizar_nome(nome))[:8] or "S"
    return conn.execute(
        "INSERT INTO subgrupos (grupo_id, codigo, nome, ativo) VALUES (?,?,?,1)",
        (grupo_id, codigo, nome),
    ).lastrowid


def _resolver_familia(conn, nome: str) -> int | None:
    if not nome:
        return None
    row = conn.execute(
        "SELECT id FROM familias WHERE LOWER(nome)=LOWER(?)", (nome,)
    ).fetchone()
    if row:
        return row["id"]
    return conn.execute(
        "INSERT INTO familias (nome, descricao) VALUES (?,?)",
        (nome, f"Importado de planilha ({nome})"),
    ).lastrowid


def importar(
    conteudo: bytes,
    nome_arquivo: str,
    usuario_id: int | None = None,
) -> dict:
    """Importa a planilha: resolve taxonomia e cria produtos como rascunho."""
    linhas = ler_planilha(conteudo, nome_arquivo)
    hash_conteudo = hashlib.sha256(conteudo).hexdigest()

    criados = 0
    atualizados = 0
    erros = 0
    erros_detalhe: list[dict] = []

    with system_conn() as conn:
        for idx, linha in enumerate(linhas, start=2):  # linha 1 = cabeçalho
            nome = (linha.get("descricao") or "").strip()
            marca = (linha.get("marca") or "").strip()
            if not nome:
                erros += 1
                erros_detalhe.append({
                    "linha": idx,
                    "status": "erro",
                    "motivo": "DESCRICAO obrigatória",
                })
                continue

            existente = conn.execute(
                "SELECT id FROM produtos_cadastro WHERE LOWER(nome)=LOWER(?)"
                " AND LOWER(COALESCE(marca,''))=LOWER(?)",
                (nome, marca),
            ).fetchone()
            if existente:
                atualizados += 1
                continue

            categoria = (linha.get("categoria") or "").strip()
            subcategoria = (linha.get("subcategoria") or "").strip()
            grupo = (linha.get("grupo") or "").strip()
            subgrupo = (linha.get("subgrupo") or "").strip()
            familia = (linha.get("familia") or "").strip()

            categoria_id, subcategoria_id = categorias.resolve(conn, categoria, subcategoria)
            grupo_id = _resolver_grupo(conn, grupo)
            subgrupo_id = _resolver_subgrupo(conn, grupo_id, subgrupo)
            familia_id = _resolver_familia(conn, familia)
            marca_id = marcas_repo.resolver(conn, marca) if marca else None

            conn.execute(
                "INSERT INTO produtos_cadastro "
                "(familia_id, nome, marca, marca_id, categoria_id, subcategoria_id,"
                " grupo_id, subgrupo_id, status_cadastro, ativo)"
                " VALUES (?,?,?,?,?,?,?,?,?,0)",
                (
                    familia_id,
                    nome,
                    marca or None,
                    marca_id,
                    categoria_id,
                    subcategoria_id,
                    grupo_id,
                    subgrupo_id,
                    "rascunho",
                ),
            )
            criados += 1

        conn.execute(
            "INSERT INTO cadastro_importacao "
            "(arquivo_nome, hash_conteudo, total, criados, atualizados, erros, status, resumo, criado_por)"
            " VALUES (?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT (hash_conteudo) DO NOTHING",
            (
                nome_arquivo,
                hash_conteudo,
                len(linhas),
                criados,
                atualizados,
                erros,
                "ok",
                json.dumps(erros_detalhe, ensure_ascii=False),
                usuario_id,
            ),
        )

    return {
        "total": len(linhas),
        "criados": criados,
        "atualizados": atualizados,
        "erros": erros,
        "erros_detalhe": erros_detalhe,
    }