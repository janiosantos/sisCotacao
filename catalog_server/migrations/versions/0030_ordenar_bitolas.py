"""0030 - Ordena opções de Bitola em ordem crescente."""
from __future__ import annotations

import json
import re
import sqlite3

VERSION = 30
NAME = "Ordenacao crescente das bitolas"


def guard(conn: sqlite3.Connection) -> bool:
    return False


def forward(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT id, opcoes FROM familia_atributos WHERE familia_id=(SELECT id FROM familias WHERE nome='Fios e Cabos') AND nome='Bitola' LIMIT 1"
    ).fetchone()
    if not row:
        return
    opcoes = json.loads(row[1] or "[]")

    def chave(valor: str) -> tuple[float, str]:
        m = re.search(r"[0-9]+(?:[,.][0-9]+)?", str(valor))
        numero = float(m.group(0).replace(",", ".")) if m else float("inf")
        return numero, str(valor).lower()

    ordenadas = sorted(dict.fromkeys(opcoes), key=chave)
    conn.execute("UPDATE familia_atributos SET opcoes=? WHERE id=?", (json.dumps(ordenadas, ensure_ascii=False), row[0]))


def backward(conn: sqlite3.Connection) -> None:
    pass
