"""0031 - Remove formatos duplicados das opções de Bitola."""
from __future__ import annotations

import json
import re
import sqlite3

VERSION = 31
NAME = "Normalizacao dos formatos de bitola"


def guard(conn: sqlite3.Connection) -> bool:
    return False


def forward(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT id FROM familia_atributos WHERE familia_id=(SELECT id FROM familias WHERE nome='Fios e Cabos') AND nome='Bitola' LIMIT 1"
    ).fetchone()
    if not row:
        return
    attr_id = row[0]
    pattern = re.compile(r"([0-9]+(?:[,.][0-9]+)?)")

    def normalizar(value: str) -> str:
        match = pattern.search(value or "")
        if not match:
            return value
        number = float(match.group(1).replace(",", "."))
        text = f"{number:.6f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"{text}mm²"

    values = [r[0] for r in conn.execute(
        "SELECT DISTINCT valor FROM variante_atributos WHERE atributo_id=?", (attr_id,)
    ).fetchall()]
    for value in values:
        conn.execute(
            "UPDATE variante_atributos SET valor=? WHERE atributo_id=? AND valor=?",
            (normalizar(value), attr_id, value),
        )
    normalized = sorted({normalizar(value) for value in values}, key=lambda v: float(pattern.search(v).group(1).replace(",", ".")))
    conn.execute("UPDATE familia_atributos SET opcoes=? WHERE id=?", (json.dumps(normalized, ensure_ascii=False), attr_id))


def backward(conn: sqlite3.Connection) -> None:
    pass
