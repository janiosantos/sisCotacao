"""Migração 0093 — Imagens: filename relativo + remoção de url_origem (v2.31.0).

Ajusta o armazenamento de imagens:
- `filename` passa a guardar o **caminho relativo** ao `IMAGES_DIR` (ex.:
  `cadastro/62470/foto_abc.jpg`), eliminando caminhos absolutos — portátil e
  facilita mudar o local de armazenamento.
- Remove a coluna `url_origem` (não mais necessária).

Os binários continuam no filesystem (`IMAGES_DIR`), nunca no banco.
"""
from __future__ import annotations

from pathlib import Path

VERSION = 93
RISCO = "critica"
NAME = "imagens_filename_relativo"

MUDANCA = {
    "o_que": [
        "filename passa a ser caminho relativo a IMAGES_DIR (sem caminho absoluto)",
        "DROP da coluna url_origem em imagens_produto",
    ],
    "porque": [
        "Caminhos absolutos quebram ao mover o diretório de imagens ou mudar de servidor",
        "url_origem não é mais necessária (as fotos já estão armazenadas)",
        "Binários permanecem no filesystem (PostgreSQL não é ideal para BLOBs de imagem em ERP)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_schema='public' AND table_name='imagens_produto'"
        "   AND column_name='url_origem'"
    ).fetchone()
    return row is None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # 1) Absolutos "…/images/cadastro/…" ou "…\images\cadastro\…" →
        #    relativos ao IMAGES_DIR (set-based, rápido e idempotente).
        cur = conn.execute(
            "UPDATE imagens_produto SET filename = substring(filename from '(?:images[/\\\\])(.*)$')"
            " WHERE filename ~ 'images[/\\\\]'"
        )
        print(f"convertidos para relativo: {cur.rowcount}")

        # 2) Normaliza separadores restantes (Windows "\\" → "/").
        cur = conn.execute(
            "UPDATE imagens_produto SET filename = replace(filename, chr(92), '/')"
            " WHERE position(chr(92) in filename) > 0"
        )
        print(f"separadores normalizados: {cur.rowcount}")

        # 3) Absolutos que não passavam por "images/" (fora de IMAGES_DIR) →
        #    só o nome do arquivo. Caso raro, poucas linhas.
        cur = conn.execute(
            "SELECT id, filename FROM imagens_produto"
            " WHERE filename LIKE '/%' OR filename ~ '^[A-Za-z]:[/\\\\]'"
        )
        alterados = 0
        for r in cur.fetchall():
            conn.execute(
                "UPDATE imagens_produto SET filename=%s WHERE id=%s",
                (Path(str(r[1])).name, r[0]),
            )
            alterados += 1
        if alterados:
            print(f"fora de IMAGES_DIR → nome: {alterados}")

        # 4) Remove url_origem.
        conn.execute("ALTER TABLE imagens_produto DROP COLUMN IF EXISTS url_origem")
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE imagens_produto ADD COLUMN IF NOT EXISTS url_origem TEXT")
    finally:
        conn.autocommit = ac