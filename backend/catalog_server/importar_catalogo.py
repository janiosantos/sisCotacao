"""Importador de catálogo no ERP a partir do JSON exportado pelo scraper.

Substitui a sincronização banco-a-banco (`sync_crawler`) que lia o `crawler.db`
diretamente. Agora o scraper exporta um arquivo JSON (ver
`app/exporters/json_exporter`) e o ERP importa esse arquivo — desacoplando as
duas aplicações.

A importação é idempotente: produtos já importados são atualizados (via
`external_id`), variantes são reconciliadas, e o histórico/cotações nunca é
apagado.

Uso:
    python -m catalog_server.importar_catalogo output/catalogo.json
"""
from __future__ import annotations

import json
from pathlib import Path

from catalog_server import categorias
from catalog_server.db import init_db, system_conn
from catalog_server.grouping import build_meta, display_name, extract_brand
from catalog_server.repositories import marcas as marcas_repo
from catalog_server.repositories import produto_repo
from catalog_server.services.sku_service import normalizar as normalizar_sku, reservar as reservar_sku

FAMILY_DISPLAY = {
    "cabo": "Cabo Flexível",
    "lampada": "Lâmpada",
    "parafuso": "Parafuso",
}

# attr_id (do enriquecimento) -> rótulo exibido na família.
FAMILY_ATTR_LABELS: dict[str, list[tuple[str, str]]] = {
    "cabo": [("color", "Cor"), ("diameter", "Bitola / Tamanho")],
    "lampada": [
        ("power", "Potência"),
        ("temperature", "Temperatura de Cor"),
        ("install", "Tipo de Instalação"),
        ("format", "Formato"),
        ("size", "Tamanho"),
    ],
    "parafuso": [
        ("diameter", "Diâmetro"),
        ("thread", "Tipo de Rosca"),
        ("head", "Tipo de Cabeça"),
        ("slot", "Tipo de Fenda"),
        ("tip", "Tipo de Ponta"),
        ("material", "Material / Tratamento"),
    ],
}


def _family_name(meta: dict, product: dict) -> str:
    family = meta.get("family")
    if family:
        return FAMILY_DISPLAY.get(family, family.capitalize())
    category = (product.get("category") or "").strip()
    return category or "Importados"


def _ensure_familia(conn, nome: str, family_key: str, values_by_attr: dict) -> tuple[int, dict[str, int]]:
    """Garante a família e retorna (familia_id, label -> atributo_id)."""
    row = conn.execute(
        "SELECT id FROM familias WHERE LOWER(nome)=LOWER(?)", (nome,)
    ).fetchone()
    if row:
        familia_id = row["id"]
    else:
        familia_id = conn.execute(
            "INSERT INTO familias (nome, descricao) VALUES (?,?)",
            (nome, f"Importado do catálogo (família {family_key})"),
        ).lastrowid

    existing = {
        r["nome"]: r["id"]
        for r in conn.execute(
            "SELECT id, nome FROM familia_atributos WHERE familia_id=?", (familia_id,)
        ).fetchall()
    }
    label_to_id: dict[str, int] = {}
    for attr_id, label in FAMILY_ATTR_LABELS.get(family_key, []):
        values = values_by_attr.get(attr_id, [])
        aid = existing.get(label)
        if aid:
            try:
                opts = json.loads(conn.execute(
                    "SELECT opcoes FROM familia_atributos WHERE id=?", (aid,)
                ).fetchone()["opcoes"] or "[]")
            except ValueError:
                opts = []
            merged = list(dict.fromkeys(opts + values))
            conn.execute(
                "UPDATE familia_atributos SET opcoes=? WHERE id=?",
                (json.dumps(merged, ensure_ascii=False), aid),
            )
        else:
            aid = conn.execute(
                "INSERT INTO familia_atributos (familia_id, nome, tipo, opcoes, ordem)"
                " VALUES (?,?,?,?,?)",
                (familia_id, label, "lista", json.dumps(values, ensure_ascii=False), len(existing) + 1),
            ).lastrowid
        label_to_id[label] = aid
    return familia_id, label_to_id


def _normalizar_produtos(produtos: list[dict]) -> list[dict]:
    """Transforma os itens do JSON no formato esperado pelo cadastro."""
    out = []
    for p in produtos:
        d = dict(p)
        d["id"] = p.get("id")
        d["attrs"] = p.get("atributos") or {}
        d["images"] = p.get("imagens") or []
        out.append(d)
    return out


def importar_catalogo(produtos: list[dict]) -> dict:
    """Importa a lista de produtos (dict do JSON) para o cadastro (idempotente)."""
    produtos = _normalizar_produtos(produtos)
    if not produtos:
        return {"produtos": 0, "criados": 0, "atualizados": 0}

    init_db()

    groups: dict[tuple, list] = {}
    for p in produtos:
        view = {
            "id": p["id"],
            "sku": p.get("sku") or "",
            "ean": p.get("ean") or "",
            "name": p.get("name") or "",
            "brand": p.get("brand") or "",
            "price": p.get("price") or 0,
            "category": p.get("category") or "",
            "subcategory": p.get("subcategory") or "",
        }
        meta = build_meta(view, p["attrs"])
        groups.setdefault(meta["key"], []).append((p, meta))

    fam_values: dict[tuple[str, str], dict] = {}
    for items in groups.values():
        for p, meta in items:
            fkey = meta.get("family")
            if not fkey:
                continue
            fname = _family_name(meta, p)
            bucket = fam_values.setdefault((fname, fkey), {})
            for attr_id, val in meta.get("attrs", {}).items():
                if val and val not in bucket.setdefault(attr_id, []):
                    bucket[attr_id].append(val)

    created = 0
    updated = 0

    with system_conn() as conn:
        family_cache: dict[str, tuple[int, dict[str, int]]] = {}
        for (fname, fkey), values in fam_values.items():
            family_cache[fname] = _ensure_familia(conn, fname, fkey, values)

        all_externals: set[str] = set()
        for (base, package), items in groups.items():
            items_sorted = sorted(items, key=lambda it: (it[0]["price"] or 0, it[0]["id"]))
            rep_p, rep_meta = items_sorted[0]

            for p, meta in items:
                ext = str(p.get("url") or p.get("sku") or f"crawler-{p['id']}").strip()
                all_externals.add(ext)
                nome = display_name(base)
                cat = p.get("category") or ""
                sub = p.get("subcategory") or ""
                marca = extract_brand(p) or (p.get("brand") or "")
                descricao = p.get("long_description") or p.get("short_description") or ""
                fname = _family_name(meta, p)
                familia_id, _ = family_cache.get(fname) or _ensure_familia(
                    conn, fname, meta.get("family") or "", {}
                )

                labels = dict(FAMILY_ATTR_LABELS.get(meta.get("family"), []))
                attrs = {}
                for aid, val in (meta.get("attrs") or {}).items():
                    if not val:
                        continue
                    label = labels.get(aid)
                    if label:
                        attrs[label] = str(val)

                found = conn.execute(
                    "SELECT id FROM produtos_cadastro WHERE external_id=?",
                    (ext,),
                ).fetchone()
                if not found and p.get("url"):
                    found = conn.execute(
                        "SELECT id FROM produtos_cadastro WHERE url=? AND url<>''",
                        (p.get("url"),),
                    ).fetchone()

                if found:
                    produto_id = found["id"]
                    categoria_id, subcategoria_id = categorias.resolve(conn, cat, sub)
                    marca_id = marcas_repo.resolver(conn, marca)
                    sku, _aviso = reservar_sku(
                        p.get("sku") or "", produto_id,
                        base=rep_p.get("name") or "", ignorar_id=produto_id, conn=conn,
                    )
                    conn.execute(
                        "UPDATE produtos_cadastro SET familia_id=?, nome=?, marca=?, marca_id=?,"
                        " descricao=?, categoria_id=?, subcategoria_id=?, embalagem=?, url=?,"
                        " external_id=?, sku=?, ean=?, preco=?, preco_promocional=?, old_price=?,"
                        " pix_price=?, atributos=?, atualizado_em=datetime('now') WHERE id=?",
                        (familia_id, nome, marca, marca_id, descricao, categoria_id,
                         subcategoria_id, package or "", p.get("url") or "", ext, sku,
                         p.get("ean") or "", p.get("price") or 0, p.get("pix_price"),
                         p.get("old_price"), p.get("pix_price"),
                         json.dumps(attrs, ensure_ascii=False), produto_id),
                    )
                    updated += 1
                else:
                    categoria_id, subcategoria_id = categorias.resolve(conn, cat, sub)
                    marca_id = marcas_repo.resolver(conn, marca)
                    produto_id = conn.execute(
                        "INSERT INTO produtos_cadastro (familia_id, nome, marca, marca_id,"
                        " descricao, categoria_id, subcategoria_id, embalagem, url, external_id,"
                        " sku, ean, preco, preco_promocional, old_price, pix_price, atributos)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (familia_id, nome, marca, marca_id, descricao, categoria_id,
                         subcategoria_id, package or "", p.get("url") or "", ext,
                         p.get("sku") or "", p.get("ean") or "", p.get("price") or 0,
                         p.get("pix_price"), p.get("old_price"), p.get("pix_price"),
                         json.dumps(attrs, ensure_ascii=False)),
                    ).lastrowid
                    sku, _aviso = reservar_sku(
                        p.get("sku") or "", produto_id,
                        base=rep_p.get("name") or "", conn=conn,
                    )
                    conn.execute(
                        "UPDATE produtos_cadastro SET sku=? WHERE id=?", (sku, produto_id)
                    )
                    created += 1

                conn.execute("DELETE FROM imagens_produto WHERE produto_id=?", (produto_id,))
                for i, img in enumerate(p.get("images", [])):
                    if not img.get("filename"):
                        continue
                    conn.execute(
                        "INSERT INTO imagens_produto (produto_id, filename, ordem)"
                        " VALUES (?,?,?)",
                        (produto_id, img["filename"], i),
                    )

        placeholders = ",".join("?" * len(all_externals))
        if all_externals:
            conn.execute(
                f"DELETE FROM produtos_cadastro WHERE external_id IS NOT NULL"
                f" AND external_id NOT IN ({placeholders})",
                list(all_externals),
            )

        # Reindexa FTS dos produtos tocados no boot (via app_factory).

    return {"produtos": len(produtos), "grupos": len(groups), "criados": created, "atualizados": updated}


def importar_arquivo(caminho: str | Path) -> dict:
    """Importa um arquivo JSON exportado pelo scraper."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    produtos = dados.get("produtos", []) if isinstance(dados, dict) else dados
    return importar_catalogo(produtos)


def importar_json_conteudo(conteudo: str) -> dict:
    """Importa a partir do conteúdo JSON (string)."""
    dados = json.loads(conteudo)
    produtos = dados.get("produtos", []) if isinstance(dados, dict) else dados
    return importar_catalogo(produtos)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m catalog_server.importar_catalogo <arquivo.json>")
        sys.exit(2)
    result = importar_arquivo(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)
