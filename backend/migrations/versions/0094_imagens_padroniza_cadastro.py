"""Migração 0094 — Padronização física das imagens em `cadastro/` (v2.31.0).

Convenções históricas de armazenamento:
- `cadastro/<produto_id>/<nome>`  — convenção ATUAL (upload, lote, URL).
- `<produto_id>/<nome>`           — convenção ANTERIOR (era do scraper).
- `<nome>` (na raiz do IMAGES_DIR) — órfãs: NÃO há arquivo físico correspondente.

O que esta migração faz:
- Move os arquivos da convenção anterior `<produto_id>/<nome>` para
  `cadastro/<produto_id>/<nome>` e atualiza `imagens_produto.filename`.
- NÃO apaga linhas órfãs (sem arquivo físico) — só são reportadas, para
  decisão consciente de limpeza posterior (destrutiva).

Binários continuam no filesystem; o banco guarda só o caminho relativo.
"""
from __future__ import annotations

from pathlib import Path

VERSION = 94
RISCO = "critica"
NAME = "imagens_padroniza_cadastro"

MUDANCA = {
    "o_que": [
        "Arquivos de imagem `images/<produto_id>/` movidos para `images/cadastro/<produto_id>/`",
        "imagens_produto.filename atualizado para a convenção cadastro/",
    ],
    "porque": [
        "Unificar o armazenamento físico de imagens numa única convenção (cadastro/<produto_id>/)",
        "Caminhos relativos + estrutura única facilitam backup, cache e mudança de local de armazenamento",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM imagens_produto"
        " WHERE filename ~ '^[0-9]+/'"
        " LIMIT 1"
    ).fetchone()
    return row is None


def forward(conn) -> None:
    from catalog_server.config import IMAGES_DIR

    ac = conn.autocommit
    conn.autocommit = True
    try:
        rows = conn.execute(
            "SELECT id, filename FROM imagens_produto"
            " WHERE filename ~ '^[0-9]+/'"
        ).fetchall()
        base = IMAGES_DIR.resolve()
        movidos = 0
        db = 0
        faltas = 0
        for r in rows:
            img_id = r[0]
            src_rel = str(r[1])
            folder = src_rel.split("/", 1)[0]
            name = src_rel.split("/", 1)[1]
            dst_rel = f"cadastro/{folder}/{name}"
            src = base / src_rel
            dst = base / dst_rel
            if src.is_file():
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists():
                        src.unlink()  # destino já existe: evita sobrescrita
                    else:
                        src.rename(dst)
                    movidos += 1
                except OSError as exc:
                    faltas += 1
                    print(f"erro movendo {src_rel}: {exc}")
            else:
                faltas += 1  # arquivo não existe fisicamente
            conn.execute(
                "UPDATE imagens_produto SET filename=%s WHERE id=%s",
                (dst_rel, img_id),
            )
            db += 1
        print(f"movidos: {movidos} | db atualizados: {db} | sem arquivo físico: {faltas}")

        # Órfãs (nome na raiz, sem arquivo físico) — apenas reportadas.
        orfas = conn.execute(
            "SELECT COUNT(*) FROM imagens_produto WHERE filename NOT LIKE '%/%'"
        ).fetchone()[0]
        print(f"linhas órfãs (sem arquivo físico): {orfas}")
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        rows = conn.execute(
            "SELECT id, filename FROM imagens_produto"
            " WHERE filename LIKE 'cadastro/%'"
        ).fetchall()
        # Revertido de forma conservadora: apenas devolve o caminho anterior
        # (o retorno físico dos arquivos exigiria restore do filesystem).
        for r in rows:
            rel = str(r[1])
            if rel.startswith("cadastro/"):
                novo = rel[len("cadastro/"):]
                conn.execute(
                    "UPDATE imagens_produto SET filename=%s WHERE id=%s",
                    (novo, r[0]),
                )
    finally:
        conn.autocommit = ac