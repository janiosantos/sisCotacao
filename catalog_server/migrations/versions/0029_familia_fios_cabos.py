"""0029 - Separa fios/cabos da familia legada e corrige Bitola."""
from __future__ import annotations

import json
import sqlite3

VERSION = 29
NAME = "Familia propria para fios e cabos"


def guard(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT 1 FROM familias WHERE nome='Fios e Cabos' LIMIT 1").fetchone()
    return bool(row)


def forward(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    family = conn.execute("SELECT id FROM familias WHERE nome='Fios e Cabos' LIMIT 1").fetchone()
    if family:
        new_family_id = family[0]
    else:
        cur = conn.execute("INSERT INTO familias (nome, descricao) VALUES (?, ?)", ("Fios e Cabos", "Fios, cabos e cordoes eletricos"))
        new_family_id = cur.lastrowid

    old_attrs = {
        r["nome"]: r for r in conn.execute(
            "SELECT * FROM familia_atributos WHERE familia_id=1 ORDER BY ordem, id"
        ).fetchall()
    }
    mapping: dict[int, int] = {}
    for old_name, new_name in (("Cor", "Cor"), ("Embalagem", "Embalagem"), ("Bitola / Tamanho", "Bitola")):
        old = old_attrs.get(old_name)
        if not old:
            continue
        existing = conn.execute(
            "SELECT id FROM familia_atributos WHERE familia_id=? AND nome=? LIMIT 1",
            (new_family_id, new_name),
        ).fetchone()
        if existing:
            new_id = existing[0]
        else:
            new_id = conn.execute(
                "INSERT INTO familia_atributos (familia_id, nome, tipo, opcoes, ordem, obrigatorio) VALUES (?,?,?,?,?,?)",
                (new_family_id, new_name, old["tipo"], old["opcoes"] or "[]", old["ordem"], old["obrigatorio"]),
            ).lastrowid
        mapping[old["id"]] = new_id

    # O nome do produto é a única evidência disponível para separar os cabos
    # da família legada; não altera variantes nem preços.
    products = conn.execute(
        """SELECT id FROM produtos_cadastro WHERE familia_id=1 AND (
             lower(trim(nome)) LIKE 'cabo %' OR lower(trim(nome)) LIKE 'fio %'
             OR lower(trim(nome)) LIKE 'cordão %' OR lower(trim(nome)) LIKE 'cordao %'
           )"""
    ).fetchall()
    product_ids = [r[0] for r in products]
    if product_ids:
        marks = ",".join("?" for _ in product_ids)
        variant_ids = [r[0] for r in conn.execute(
            f"SELECT id FROM variantes WHERE produto_id IN ({marks})", product_ids
        ).fetchall()]
        if variant_ids and mapping:
            vm = ",".join("?" for _ in variant_ids)
            for old_id, new_id in mapping.items():
                conn.execute(
                    f"UPDATE variante_atributos SET atributo_id=? WHERE atributo_id=? AND variante_id IN ({vm})",
                    [new_id, old_id, *variant_ids],
                )
        conn.execute(f"UPDATE produtos_cadastro SET familia_id=? WHERE id IN ({marks})", [new_family_id, *product_ids])

    # Os demais itens da família eram objetos não relacionados a cabos.
    # Retira apenas o vínculo de família, preservando produto e variantes para
    # reclassificação posterior.
    conn.execute(
        "UPDATE familias SET nome='Itens legados - reclassificar', descricao='Itens que estavam incorretamente na familia de cabos' WHERE id=1"
    )
    conn.execute(
        "UPDATE produtos_cadastro SET familia_id=NULL WHERE familia_id=1"
    )

    # Remove artefato explícito de teste que contaminava a matriz do cabo.
    conn.execute(
        """UPDATE variantes SET ativo=0 WHERE id IN (
          SELECT va.variante_id FROM variante_atributos va WHERE va.valor='Teste 99'
        )"""
    )
    conn.execute("DELETE FROM variante_atributos WHERE valor='Teste 99'")


def backward(conn: sqlite3.Connection) -> None:
    # Não desfaz reclassificação de dados automaticamente.
    pass
