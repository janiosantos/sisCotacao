# -*- coding: utf-8 -*-
r"""Popula fornecedor_variantes com distribuidores B2B de materiais
elétricos/hidráulicos, parafusos, ferramentas e casa & jardim (região SE).

Idempotente: adiciona fornecedores inexistentes e usa INSERT OR IGNORE
(respeita UNIQUE(variante_id, fornecedor_id)). Rode com:
>.venv\Scripts\python.exe catalog_server\scripts_populate_suppliers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from catalog_server.db import system_conn  # noqa: E402

# Fornecedores a garantir (nome -> observação). TAMBASA/NEGRAO já existem e
# são mantidos (distribuidores de material de construção do SE).
SUPPLIERS = {
    "Alfa Materiais Elétricos": "Material elétrico · São Paulo/SP",
    "Eletro Farias": "Material elétrico e iluminação · São Paulo/SP",
    "Casa das Lâmpadas": "Iluminação e lâmpadas · São Paulo/SP",
    "Hidro Tubos": "Hidráulica e conexões · São Paulo/SP",
    "Casa do Encanador": "Tubos, conexões e torneiras · São Paulo/SP",
    "Construfer": "Ferragens, fixadores e construção · São Paulo/SP",
    "Ferragens Martinez": "Parafusos e ferragens · São Paulo/SP",
    "Famastil Ferramentas": "Ferramentas · São Paulo/SP",
    "Ferrfer Ferramentas": "Ferramentas e acessórios · São Paulo/SP",
    "Casa do Construtor": "Construção, casa e jardim · São Paulo/SP",
    "Epimed": "EPI · Belo Horizonte/MG",
}

_NORM = str.casefold

# categoria (normalizada) -> grupo. Regras avaliadas em ordem; qualquer
# correspondência adiciona os fornecedores do grupo. Se "ferramenta" casar,
# o grupo ELÉTRICO é descartado (ferramentas elétricas não são mat. elétrico).
RULES = [
    ("ELETRICO", ["elétrico", "fios e cabos", "lâmpad", "ilumin", "luminária",
                  "refletor", "spot", "chuveiro", "led"],
     ["Alfa Materiais Elétricos", "Eletro Farias", "Casa das Lâmpadas", "TAMBASA"]),
    ("HIDRAULICO", ["hidráulica", "torneira", "registro", "cano", "tubo",
                    "chuveiro", "pvc"],
     ["Hidro Tubos", "Casa do Encanador", "NEGRAO"]),
    ("FERRAMENTAS", ["ferrament", "abrasivo", "solda", "compressor", "medição",
                     "medida", "máquina", "marceneira", "bateria"],
     ["Famastil Ferramentas", "Ferrfer Ferramentas", "NEGRAO"]),
    ("FIXADORES", ["fixador", "fixação", "ferragem", "parafuso", "porca",
                   "arruela", "bucha", "contrapino"],
     ["Construfer", "Ferragens Martinez", "TAMBASA"]),
    ("EPI", ["epi", "segurança", "vigilância", "alarme", "câmera"],
     ["Epimed"]),
    ("CASA_JARDIM_CONSTR", ["casa e jardim", "jardim", "jardinagem", "construção",
                            "organização", "armazenagem", "limpeza", "automotivo",
                            "movimentação", "funilaria", "aditivo", "cola",
                            "adesivo", "lubrificante", "agronegócio", "natalino",
                            "preventivo", "promoção", "cupom", "limitado"],
     ["Casa do Construtor", "Construfer", "TAMBASA", "NEGRAO"]),
]

GENERAL = ["Casa do Construtor", "Construfer", "TAMBASA", "NEGRAO"]


def suppliers_for(categoria: str | None) -> list[str]:
    cat = _NORM(categoria or "")
    groups = []
    for _name, keys, sups in RULES:
        if any(k in cat for k in keys):
            groups.append((_name, sups))
    # ferramentas elétricas: descarta ELÉTRICO
    if any(g[0] == "FERRAMENTAS" for g in groups):
        groups = [g for g in groups if g[0] != "ELETRICO"]
    names = []
    for _n, sups in groups:
        for s in sups:
            if s not in names:
                names.append(s)
    return names or list(GENERAL)


def main() -> None:
    with system_conn() as conn:
        existing = {r["nome"] for r in conn.execute("SELECT nome FROM fornecedores").fetchall()}
        to_add = [n for n in SUPPLIERS if n not in existing]
        for nome in to_add:
            conn.execute(
                "INSERT INTO fornecedores (nome, whatsapp, email, observacoes, ativo)"
                " VALUES (?, NULL, NULL, ?, 1)",
                (nome, SUPPLIERS[nome]),
            )
        name2id = {r["nome"]: r["id"] for r in conn.execute("SELECT id, nome FROM fornecedores").fetchall()}

        # todas as variantes ativas, com o nome da categoria do produto
        rows = conn.execute(
            """
            SELECT v.id AS variante_id, cat.nome AS categoria
            FROM variantes v
            JOIN produtos_cadastro p ON p.id=v.produto_id AND p.ativo=1
            LEFT JOIN categorias cat ON cat.id=p.categoria_id
            WHERE v.ativo=1
            """
        ).fetchall()

        batch = []
        stats: dict[str, int] = {}
        for r in rows:
            names = suppliers_for(r["categoria"])
            if names:
                stats.setdefault(r["categoria"], 0)
                stats[r["categoria"]] += 1
            for nome in names:
                fid = name2id.get(nome)
                if fid is None:
                    continue
                batch.append((r["variante_id"], fid, "", "", "", 1.0))

        before = conn.execute("SELECT COUNT(*) FROM fornecedor_variantes").fetchone()[0]
        conn.executemany(
            "INSERT OR IGNORE INTO fornecedor_variantes"
            " (variante_id, fornecedor_id, codigo_fornecedor, descricao_fornecedor,"
            "  unidade_compra, fator_conversao) VALUES (?,?,?,?,?,?)",
            batch,
        )
        after = conn.execute("SELECT COUNT(*) FROM fornecedor_variantes").fetchone()[0]
        print(f"fornecedores adicionados: {len(to_add)} ({sorted(to_add)})")
        print(f"variantes ativas avaliadas: {len(rows)}")
        print(f"Fornecedor variantes: antes={before} -> depois={after} (novos={after - before})")
        covered = sum(1 for r in rows if r["categoria"] in stats)
        print(f"categorias distintas: {len(stats)} | variantes com cobertura: {len(rows)}")


if __name__ == "__main__":
    main()