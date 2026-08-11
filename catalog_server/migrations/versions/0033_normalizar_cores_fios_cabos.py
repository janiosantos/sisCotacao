"""0033 - Normaliza cores da familia Fios e Cabos."""
from __future__ import annotations

import json
import sqlite3

VERSION = 33
NAME = "Normalizacao das cores de fios e cabos"

CORES = [
    "Amarelo", "Azul", "Azul Claro", "Branco", "Cinza", "Marrom",
    "Preto", "Transparente", "Verde", "Verde Claro", "Verde/Amarelo",
    "Vermelho", "Multicor",
]


def guard(conn: sqlite3.Connection) -> bool:
    return False


def forward(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT id FROM familia_atributos WHERE familia_id=(SELECT id FROM familias WHERE nome='Fios e Cabos') AND nome='Cor' LIMIT 1"
    ).fetchone()
    if not row:
        return
    attr_id = row[0]
    aliases = {
        "amarelo": "Amarelo", "azul": "Azul", "ceu": "Azul Claro",
        "branco": "Branco", "cinza": "Cinza", "marrom": "Marrom",
        "preto": "Preto", "transparente": "Transparente", "verde": "Verde",
        "verde claro": "Verde Claro", "verde amerelo": "Verde/Amarelo",
        "vermelho": "Vermelho", "multicor": "Multicor",
    }
    rows = conn.execute("SELECT id, valor FROM variante_atributos WHERE atributo_id=?", (attr_id,)).fetchall()
    for item_id, value in rows:
        normalized = aliases.get((value or "").strip().lower())
        if normalized:
            conn.execute("UPDATE variante_atributos SET valor=? WHERE id=?", (normalized, item_id))
        elif (value or "").strip().lower() == "cor x":
            conn.execute("DELETE FROM variante_atributos WHERE id=?", (item_id,))
    conn.execute("UPDATE familia_atributos SET opcoes=? WHERE id=?", (json.dumps(CORES, ensure_ascii=False), attr_id))


def backward(conn: sqlite3.Connection) -> None:
    pass
