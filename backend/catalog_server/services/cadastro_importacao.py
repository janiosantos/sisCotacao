"""Workflow de cadastro e importa����o em lote (MDM-006).

- `produtos_cadastro.status_cadastro`: rascunho �?' em_revisao �?' publicado �?' bloqueado.
  Publicar = ativo 1; demais estados = ativo 0 (n�o vendido / fora do cat�logo p�blico).
- Importa����o: preview por linha, deduplica��o por SKU/EAN/nome+marca, cria novos
  como rascunho (revis�o antes de publicar) e n�o grava parcialmente sem registrar
  o resultado. Reprocessar o mesmo arquivo (hash) n�o duplica.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from catalog_server.db import system_conn

STATUS_VALIDOS = ["rascunho", "em_revisao", "publicado", "bloqueado"]
_ATIVO_POR_STATUS = {"publicado": 1, "rascunho": 0, "em_revisao": 0, "bloqueado": 0}

TRANSICOES: dict[str, set[str]] = {
    "rascunho": {"em_revisao", "publicado", "bloqueado"},
    "em_revisao": {"publicado", "rascunho", "bloqueado"},
    "publicado": {"bloqueado", "rascunho", "em_revisao"},
    "bloqueado": {"publicado", "rascunho"},
}


def set_status_cadastro(produto_id: int, novo: str, usuario_id: int | None = None) -> str:
    novo = (novo or "").strip().lower()
    if novo not in STATUS_VALIDOS:
        raise ValueError("status_cadastro inv�lido")
    with system_conn() as conn:
        atual = conn.execute(
            "SELECT status_cadastro FROM produtos_cadastro WHERE id=?", (produto_id,)
        ).fetchone()
        if not atual:
            raise LookupError("produto n�o encontrado")
        origem = (atual["status_cadastro"] or "publicado")
        if origem == novo:
            return novo
        if novo not in TRANSICOES.get(origem, set()):
            raise ValueError(f"transi��o inv�lida: {origem} -> {novo}")
        conn.execute(
            "UPDATE produtos_cadastro SET status_cadastro=?, ativo=?, atualizado_em=NOW() "
            "WHERE id=?",
            (novo, _ATIVO_POR_STATUS[novo], produto_id),
        )
    return novo


def _normalizar_linha(linha: dict, idx: int) -> dict:
    nome = (linha.get("nome") or "").strip()
    sku = (linha.get("sku") or "").strip()
    ean = "".join(c for c in (linha.get("ean") or "") if c.isdigit())
    marca = (linha.get("marca") or "").strip()
    if not nome:
        return {"linha": idx, "status": "erro", "motivo": "nome obrigat�rio"}
    if ean and len(ean) not in (8, 12, 13, 14):
        return {"linha": idx, "status": "erro", "motivo": "EAN inv�lido"}
    try:
        preco = Decimal(str(linha.get("preco") or 0))
    except (TypeError, ValueError):
        preco = Decimal("0")
    if preco < 0:
        return {"linha": idx, "status": "erro", "motivo": "pre�o negativo"}
    return {
        "linha": idx,
        "status": "ok",
        "nome": nome,
        "sku": sku,
        "ean": ean,
        "marca": marca,
        "preco": preco,
        "unidade_venda": (linha.get("unidade_venda") or "UN").strip().upper()[:10] or "UN",
    }


def _achou_existente(conn, nome: str, sku: str, ean: str, marca: str):
    if sku:
        r = conn.execute(
            "SELECT id FROM produtos_cadastro WHERE sku=? LIMIT 1", (sku,)
        ).fetchone()
        if r:
            return r["id"], "sku"
    if ean:
        r = conn.execute(
            "SELECT id FROM produtos_cadastro WHERE ean=? LIMIT 1", (ean,)
        ).fetchone()
        if r:
            return r["id"], "ean"
    if nome and marca:
        r = conn.execute(
            "SELECT id FROM produtos_cadastro WHERE LOWER(nome)=LOWER(?) AND LOWER(marca)=LOWER(?) LIMIT 1",
            (nome, marca),
        ).fetchone()
        if r:
            return r["id"], "nome+marca"
    return None, None


def preview(rows: list[dict]) -> dict:
    linhas = [_normalizar_linha(r, idx) for idx, r in enumerate(rows, start=1)]
    erros = sum(1 for l in linhas if l["status"] == "erro")
    return {"total": len(rows), "erros": erros, "linhas": linhas}


def importar(
    rows: list[dict],
    arquivo_nome: str | None = None,
    usuario_id: int | None = None,
) -> dict:
    arquivo = (arquivo_nome or "importacao.json").strip()
    conteudo = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    hash_conteudo = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    with system_conn() as conn:
        existente = conn.execute(
            "SELECT id, total, criados, atualizados, erros FROM cadastro_importacao "
            "WHERE hash_conteudo=?",
            (hash_conteudo,),
        ).fetchone()
        if existente:
            return {
                "id": existente["id"],
                "duplicado": True,
                "total": existente["total"],
                "criados": existente["criados"],
                "atualizados": existente["atualizados"],
                "erros": existente["erros"],
            }

        criados = 0
        atualizados = 0
        erros = 0
        erros_detalhe: list[dict] = []
        for idx, linha in enumerate(rows, start=1):
            n = _normalizar_linha(linha, idx)
            if n["status"] == "erro":
                erros += 1
                erros_detalhe.append(n)
                continue
            existente_id, por = _achou_existente(conn, n["nome"], n["sku"], n["ean"], n["marca"])
            if existente_id:
                atualizados += 1
                continue
            conn.execute(
                "INSERT INTO produtos_cadastro "
                "(nome, ativo, sku, ean, preco, unidade_venda, marca, status_cadastro) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    n["nome"],
                    0,  # rascunho: fora de venda/cat�logo at� publicar
                    n["sku"] or None,
                    n["ean"] or None,
                    n["preco"],
                    n["unidade_venda"],
                    n["marca"] or None,
                    "rascunho",
                ),
            )
            criados += 1

        novo_id = conn.execute(
            "INSERT INTO cadastro_importacao "
            "(arquivo_nome, hash_conteudo, total, criados, atualizados, erros, status, resumo, criado_por) "
            "VALUES (?,?,?,?,?,?,?,?,?) RETURNING id",
            (
                arquivo,
                hash_conteudo,
                len(rows),
                criados,
                atualizados,
                erros,
                "ok",
                json.dumps(erros_detalhe, ensure_ascii=False),
                usuario_id,
            ),
        ).fetchone()["id"]

        return {
            "id": novo_id,
            "duplicado": False,
            "total": len(rows),
            "criados": criados,
            "atualizados": atualizados,
            "erros": erros,
        }