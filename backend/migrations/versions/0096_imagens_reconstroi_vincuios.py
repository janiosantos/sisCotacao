"""Migração 0096 — Reconstrói vínculos de imagem a partir do filesystem (v2.31.0).

REPARO DE DADOS. A migração 0095 apagou linhas de `imagens_produto` cujo
`filename` não tinha diretório (nomes "pelados"), geradas por uma execução
anterior da 0093 que perdeu a pasta `cadastro/<produto_id>/`. Esses nomes
"pelados" NÃO indicavam arquivo inexistente: os arquivos estão presentes em
`images/cadastro/<produto_id>/<nome>`.

Esta migração religa as imagens usando o FILESYSTEM como fonte da verdade:
para cada arquivo sob `cadastro/<id>/`, se o produto existe e ainda não há
linha com esse filename, insere `(produto_id, 'cadastro/<id>/<nome>', ordem)`.

Idempotente: reexecutar não duplica (verifica filename existente). Em
ambientes sem órfãos (produção), insere 0 linhas.
"""
from __future__ import annotations

VERSION = 96
RISCO = "critica"
NAME = "imagens_reconstroi_vincuios"

MUDANCA = {
    "o_que": [
        "Reconstrói linhas de imagens_produto perdidas, a partir dos arquivos existentes em images/cadastro/<produto_id>/",
    ],
    "porque": [
        "Restaura imagens de produtos cujos vínculos foram apagados indevidamente pela 0095 (arquivos reais continuavam no disco)",
        "Fonte da verdade = filesystem; nenhum arquivo é movido ou apagado",
    ],
}


def guard(conn) -> bool:
    # Sempre roda o forward: a reconstrução é idempotente e depende do
    # filesystem (não dá para deduzir o estado-alvo só pelo banco).
    return False


def forward(conn) -> None:
    from catalog_server.config import IMAGES_DIR

    base = (IMAGES_DIR.resolve() / "cadastro")
    ac = conn.autocommit
    conn.autocommit = False
    try:
        if not base.exists():
            conn.commit()
            print("cadastro/ inexistente — nada a reconstruir")
            return

        produtos = set(r[0] for r in conn.execute("SELECT id FROM produtos_cadastro").fetchall())
        existentes = set(r[0] for r in conn.execute("SELECT filename FROM imagens_produto").fetchall())
        max_ordem = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT produto_id, COALESCE(MAX(ordem), -1)"
                " FROM imagens_produto GROUP BY produto_id"
            ).fetchall()
        }

        criadas = 0
        produtos_ignorados = 0
        for d in base.iterdir():
            if not d.is_dir() or not d.name.isdigit():
                continue
            pid = int(d.name)
            if pid not in produtos:
                produtos_ignorados += 1
                continue
            prox = max_ordem.get(pid, -1) + 1
            for f in sorted(f for f in d.iterdir() if f.is_file()):
                rel = f"cadastro/{pid}/{f.name}"
                if rel in existentes:
                    continue
                conn.execute(
                    "INSERT INTO imagens_produto (produto_id, filename, ordem)"
                    " VALUES (%s, %s, %s)",
                    (pid, rel, prox),
                )
                existentes.add(rel)
                prox += 1
                criadas += 1
        conn.commit()
        print(f"linhas reconstruídas: {criadas} | pastas de produtos inexistentes ignoradas: {produtos_ignorados}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    # Reparo de dados: não há rollback semântico seguro (as linhas originais
    # não existem mais). Requer restore do backup pré-migração.
    raise NotImplementedError("backward requer restore do backup pré-migração")