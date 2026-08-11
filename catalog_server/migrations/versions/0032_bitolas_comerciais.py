"""0032 - Lista oficial de bitolas comerciais de fios e cabos."""
from __future__ import annotations

import json
import sqlite3

VERSION = 32
NAME = "Lista oficial de bitolas comerciais"

BITOLAS = [
    "0,5mm²", "0,75mm²", "1,0mm²", "1,5mm²", "2,5mm²", "4,0mm²",
    "6,0mm²", "10mm²", "16mm²", "25mm²", "35mm²", "50mm²", "70mm²",
    "95mm²", "120mm²", "150mm²", "185mm²", "240mm²",
]


def guard(conn: sqlite3.Connection) -> bool:
    return False


def forward(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT id FROM familia_atributos WHERE familia_id=(SELECT id FROM familias WHERE nome='Fios e Cabos') AND nome='Bitola' LIMIT 1"
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE familia_atributos SET opcoes=? WHERE id=?",
            (json.dumps(BITOLAS, ensure_ascii=False), row[0]),
        )


def backward(conn: sqlite3.Connection) -> None:
    pass
