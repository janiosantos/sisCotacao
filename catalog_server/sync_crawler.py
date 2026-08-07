"""Sincroniza o banco do scraper (crawler.db) com o cadastro (server.db).

Unifica catálogo e cadastro em uma única base (`server.db`): cada grupo de
produtos do crawler (mesma base + embalagem) vira um `produtos_cadastro` (pai)
e cada produto do crawler vira uma `variante`, com seus atributos e imagens.

A sincronização é idempotente: produtos já sincronizados são atualizados (via
`external_id`) em vez de duplicados. Produtos cadastrados manualmente (sem
`external_id`) nunca são alterados. Após sincronizar, remapeia
`cotacao_itens.produto_id` (que referenciava ids do crawler) para os novos ids
de variante, preservando cotações e histórico.

Uso: `python -m catalog_server.sync_crawler`
"""
from __future__ import annotations

import json
import sqlite3

from catalog_server import config, categorias
from catalog_server.db import init_db, system_conn
from catalog_server.grouping import build_meta, display_name, extract_brand

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


def _load_crawler() -> list[dict]:
    """Carrega produtos parseados com atributos e imagens do crawler.db."""
    if not config.CATALOG_DB.exists():
        return []
    conn = sqlite3.connect(
        f"file:{config.CATALOG_DB.resolve().as_posix()}?mode=ro", uri=True
    )
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM products WHERE parsed=1").fetchall()
        attrs_map: dict[int, dict] = {}
        try:
            for r in conn.execute(
                "SELECT product_id, attr, value FROM product_attributes"
            ):
                attrs_map.setdefault(r["product_id"], {})[r["attr"]] = r["value"]
        except sqlite3.OperationalError:
            pass
        imgs_map: dict[int, list] = {}
        for r in conn.execute(
            "SELECT product_id, filename, url FROM images ORDER BY id"
        ):
            imgs_map.setdefault(r["product_id"], []).append(
                {"filename": r["filename"], "url": r["url"]}
            )
    finally:
        conn.close()

    products = []
    for r in rows:
        d = dict(r)
        d["attrs"] = attrs_map.get(d["id"], {})
        d["images"] = imgs_map.get(d["id"], [])
        products.append(d)
    return products


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
            (nome, f"Sincronizada do scraper (família {family_key})"),
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


def sync_crawler() -> dict:
    products = _load_crawler()
    if not products:
        return {"produtos": 0, "criados": 0, "atualizados": 0}

    init_db()

    groups: dict[tuple, list] = {}
    for p in products:
        view = {
            "id": p["id"],
            "sku": p["sku"],
            "ean": p["ean"],
            "name": p["name"],
            "brand": p["brand"],
            "price": p["price"],
            "category": p["category"],
            "subcategory": p["subcategory"],
        }
        meta = build_meta(view, p["attrs"])
        groups.setdefault(meta["key"], []).append((p, meta))

    # Valores distintos por atributo em cada família (para as opções).
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
    remap: dict[int, int] = {}

    with system_conn() as conn:
        family_cache: dict[str, tuple[int, dict[str, int]]] = {}
        for (fname, fkey), values in fam_values.items():
            family_cache[fname] = _ensure_familia(conn, fname, fkey, values)

        for (base, package), items in groups.items():
            items_sorted = sorted(items, key=lambda it: (it[0]["price"] or 0, it[0]["id"]))
            rep_p, rep_meta = items_sorted[0]
            nome = display_name(base)
            cat = rep_p.get("category") or ""
            sub = rep_p.get("subcategory") or ""
            marca = extract_brand(rep_p) or ""
            descricao = (
                rep_p.get("long_description")
                or rep_p.get("short_description")
                or ""
            )
            fname = _family_name(rep_meta, rep_p)
            familia_id, label_to_id = family_cache.get(fname) or _ensure_familia(
                conn, fname, rep_meta.get("family") or "", {}
            )
            current_external = {p["id"] for p, _ in items}

            found = conn.execute(
                "SELECT id FROM produtos_cadastro WHERE external_id=?",
                (rep_p["id"],),
            ).fetchone()
            if not found:
                # O representante pode ter mudado (re-scrape): adota o produto que
                # já guarda as variantes deste grupo (mesmos produtos do crawler).
                for member in current_external:
                    vrow = conn.execute(
                        "SELECT produto_id FROM variantes WHERE external_id=? AND external_id IS NOT NULL LIMIT 1",
                        (member,),
                    ).fetchone()
                    if vrow:
                        found = vrow
                        break
            if found:
                produto_id = found["id"]
                categoria_id, subcategoria_id = categorias.resolve(conn, cat, sub)
                conn.execute(
                    "UPDATE produtos_cadastro SET familia_id=?, nome=?, marca=?,"
                    " descricao=?, categoria_id=?, subcategoria_id=?, embalagem=?, url=?,"
                    " external_id=?, atualizado_em=datetime('now') WHERE id=?",
                    (familia_id, nome, marca, descricao, categoria_id, subcategoria_id,
                     package or "", rep_p.get("url") or "", rep_p["id"], produto_id),
                )
                updated += 1
            else:
                categoria_id, subcategoria_id = categorias.resolve(conn, cat, sub)
                produto_id = conn.execute(
                    "INSERT INTO produtos_cadastro (familia_id, nome, marca, descricao,"
                    " categoria_id, subcategoria_id, embalagem, url, external_id)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (familia_id, nome, marca, descricao, categoria_id, subcategoria_id,
                     package or "", rep_p.get("url") or "", rep_p["id"]),
                ).lastrowid
                created += 1

            for p, meta in items:
                vrow = conn.execute(
                    "SELECT id FROM variantes WHERE produto_id=? AND external_id=?",
                    (produto_id, p["id"]),
                ).fetchone()
                if vrow:
                    vid = vrow["id"]
                    conn.execute(
                        "UPDATE variantes SET sku=?, ean=?, preco=?, preco_promocional=?,"
                        " old_price=?, pix_price=?, installment=?, url=?, marca=?, ativo=1 WHERE id=?",
                        (p.get("sku") or "", p.get("ean") or "", p.get("price") or 0,
                         p.get("pix_price"), p.get("old_price"), p.get("pix_price"),
                         p.get("installment") or "", p.get("url") or "",
                         extract_brand(p) or (p.get("brand") or ""), vid),
                    )
                else:
                    vid = conn.execute(
                        "INSERT INTO variantes (produto_id, sku, ean, preco,"
                        " preco_promocional, old_price, pix_price, installment, url, external_id, marca)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (produto_id, p.get("sku") or "", p.get("ean") or "",
                         p.get("price") or 0, p.get("pix_price"), p.get("old_price"),
                         p.get("pix_price"), p.get("installment") or "",
                         p.get("url") or "", p["id"], extract_brand(p) or (p.get("brand") or "")),
                    ).lastrowid
                remap[p["id"]] = vid

                conn.execute(
                    "DELETE FROM variante_atributos WHERE variante_id=?", (vid,)
                )
                for attr_id, val in meta.get("attrs", {}).items():
                    if not val:
                        continue
                    label = dict(FAMILY_ATTR_LABELS.get(meta.get("family"), [])).get(attr_id)
                    aid = label_to_id.get(label) if label else None
                    if aid:
                        conn.execute(
                            "INSERT INTO variante_atributos (variante_id, atributo_id, valor)"
                            " VALUES (?,?,?)",
                            (vid, aid, str(val)),
                        )

                conn.execute(
                    "DELETE FROM imagens_produto WHERE variante_id=?", (vid,)
                )
                for i, img in enumerate(p.get("images", [])):
                    if not img.get("filename"):
                        continue
                    conn.execute(
                        "INSERT INTO imagens_produto (produto_id, variante_id, filename,"
                        " url_origem, ordem) VALUES (?,?,?,?,?)",
                        (produto_id, vid, img["filename"], img.get("url") or "", i),
                    )

            placeholders = ",".join("?" * len(current_external))
            conn.execute(
                f"DELETE FROM variantes WHERE produto_id=? AND external_id IS NOT NULL"
                f" AND external_id NOT IN ({placeholders})",
                [produto_id] + list(current_external),
            )

        # Preserva cotações/histórico: remapeia antigos ids do crawler para
        # variantes. Executa UMA vez (os ids de variante não devem voltar a
        # referenciar produtos do crawler nas rodadas seguintes).
        sync_row = conn.execute(
            "SELECT cotacao_remap_done FROM scraper_sync WHERE id=1"
        ).fetchone()
        remap_done = bool(sync_row and sync_row["cotacao_remap_done"])
        if not remap_done:
            for row in conn.execute("SELECT id, produto_id FROM cotacao_itens").fetchall():
                old = row["produto_id"]
                if old in remap and remap[old] != old:
                    conn.execute(
                        "UPDATE cotacao_itens SET produto_id=? WHERE id=?",
                        (remap[old], row["id"]),
                    )
            conn.execute(
                "INSERT INTO scraper_sync (id, cotacao_remap_done, atualizado_em)"
                " VALUES (1, 1, datetime('now'))"
                " ON CONFLICT(id) DO UPDATE SET cotacao_remap_done=1, atualizado_em=datetime('now')"
            )

    return {
        "produtos": len(products),
        "grupos": len(groups),
        "criados": created,
        "atualizados": updated,
    }


if __name__ == "__main__":
    import sys

    result = sync_crawler()
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)
