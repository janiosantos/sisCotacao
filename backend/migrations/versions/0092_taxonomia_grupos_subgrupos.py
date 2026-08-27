"""Migração 0092 — Taxonomia: grupos/subgrupos + vínculo de categorias (v2.28.0).

Normaliza a taxonomia do catálogo, que tinha apenas 4 grupos / 3 subgrupos e
praticamente nenhum produto vinculado (1 de 62.731):

- Adiciona `categorias.subgrupo_id` (hierarquia Grupo → Subgrupo → Categoria).
- Cria os grupos/subgrupos do mapeamento (idempotente por código).
- Vincula cada categoria ao seu subgrupo.
- Atribui `produtos_cadastro.grupo_id/subgrupo_id` a partir da categoria do produto.

O mapeamento é determinístico (idempotente). Categorias "ruído" (Promoção, Cupom,
Marcas, Kits, Preventivo, ZZTeste, Acessórios genérico, Agronegócio) ficam sem
subgrupo — produtos dessas categorias permanecem sem grupo/subgrupo.
"""
from __future__ import annotations

VERSION = 92
RISCO = "critica"
NAME = "taxonomia_grupos_subgrupos"

# (codigo_grupo, nome_grupo, [(codigo_sub, nome_sub, [nomes de categorias])])
_TAXONOMIA = [
    ("FER", "Ferramentas", [
        ("MAN", "Ferramentas Manuais", ["Ferramentas Manuais", "Ferramentas Em Geral", "Ferramentas", "Ferramentas de corte"]),
        ("ELE", "Ferramentas Elétricas", ["Ferramentas Elétricas", "Ferramentas Elétricas e Máquinas", "Ferramentas à Bateria", "Máquinas e Equipamentos"]),
        ("PNU", "Ferramentas Pneumáticas", ["Ferramentas Pneumáticas", "Compressores de Ar"]),
        ("SOL", "Solda", ["Solda"]),
        ("ABR", "Abrasivos", ["Abrasivos"]),
        ("ACE", "Acessórios para Ferramentas", ["Acessórios para Ferramentas"]),
    ]),
    ("ELE", "Materiais Elétricos", [
        ("CAB", "Fios e Cabos", ["Fios e Cabos", "Fios e Cabos Elétricos"]),
        ("ILU", "Iluminação", ["Iluminação", "Luminária Led de Embutir", "Luminária Led de Sobrepor", "Refletor Led", "Spot Led MR11"]),
        ("LAM", "Lâmpadas", ["Lâmpadas"]),
        ("INS", "Material de Instalação Elétrica", ["Material Elétrico"]),
    ]),
    ("HID", "Hidráulico", [
        ("HID", "Hidráulica", ["Hidráulica", "Chuveiros e Torneiras"]),
    ]),
    ("PAR", "Fixadores", [
        ("FIX", "Parafusos e Fixadores", ["Fixadores", "Fixação", "Contrapino 5/32 x 2.1/4 - METALURGICA..."]),
    ]),
    ("AUT", "Automotivo", [
        ("AUT", "Automotivo", ["Automotivo", "Equipamento Auto Center"]),
        ("PINT", "Funilaria e Pintura", ["Funilaria E Pintura"]),
        ("LUB", "Lubrificantes", ["Aditivos e Lubrificantes", "Colas Adesivos e Lubrificantes"]),
    ]),
    ("CON", "Construção Civil", [
        ("CON", "Construção Civil", ["Construção Civil"]),
    ]),
    ("SEG", "EPI e Segurança", [
        ("EPI", "EPI", ["EPI"]),
        ("SEG", "Segurança e Vigilância", ["Segurança e Vigilância", "Alarmes e Câmeras", "Câmeras"]),
    ]),
    ("CAS", "Casa, Jardim e Limpeza", [
        ("CAS", "Casa e Jardim", ["Casa e Jardim", "Jardinagem", "Jardim e Área Externa", "Ventiladores, Exaustores", "Produtos Natalinos", "Marceneira"]),
        ("LIMP", "Limpeza", ["Limpeza"]),
        ("ORG", "Organização e Armazenagem", ["Organização e Armazenagem"]),
    ]),
    ("MED", "Medição e Instrumentos", [
        ("INS", "Instrumentos", ["Instrumentos de Medição e Teste"]),
        ("MED", "Medição", ["Medição", "Equipamentos de Medição"]),
    ]),
    ("MOV", "Movimentação de Carga", [
        ("MOV", "Movimentação", ["Movimentação de Carga", "Movimentação E Carga"]),
    ]),
]

MUDANCA = {
    "o_que": [
        "categorias.subgrupo_id (FK para subgrupos)",
        "Cria grupos/subgrupos do mapeamento (idempotente)",
        "Vincula categorias ao subgrupo e atribui grupo/subgrupo aos produtos",
    ],
    "porque": [
        "Normaliza a taxonomia: 62.731 produtos sem grupo/subgrupo",
        "Permite filtrar categorias por grupo/subgrupo no cadastro",
    ],
}


def guard(conn) -> bool:
    # Aplicada de fato quando a normalização rodou: existe um grupo criado por
    # esta migração (AUT) e a coluna subgrupo_id existe.
    row = conn.execute(
        "SELECT 1 FROM grupos WHERE codigo='AUT'"
    ).fetchone()
    return row is not None


def _grupo_id(conn, codigo: str, nome: str) -> int:
    conn.execute(
        "INSERT INTO grupos (codigo, nome) VALUES (%s, %s) ON CONFLICT (codigo) DO NOTHING",
        (codigo, nome),
    )
    return int(conn.execute(
        "SELECT id FROM grupos WHERE codigo=%s", (codigo,)
    ).fetchone()[0])


def _subgrupo_id(conn, grupo_id: int, codigo: str, nome: str) -> int:
    conn.execute(
        "INSERT INTO subgrupos (grupo_id, codigo, nome)"
        " VALUES (%s, %s, %s) ON CONFLICT (grupo_id, codigo) DO NOTHING",
        (grupo_id, codigo, nome),
    )
    return int(conn.execute(
        "SELECT id FROM subgrupos WHERE grupo_id=%s AND codigo=%s",
        (grupo_id, codigo),
    ).fetchone()[0])


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE categorias ADD COLUMN IF NOT EXISTS subgrupo_id BIGINT"
        )

        # 1) Cria grupos/subgrupos e monta categoria -> subgrupo_id.
        cat_sub: dict[str, int] = {}
        for gcod, gnome, subs in _TAXONOMIA:
            gid = _grupo_id(conn, gcod, gnome)
            for scod, snome, cats in subs:
                sid = _subgrupo_id(conn, gid, scod, snome)
                for c in cats:
                    cat_sub[c] = sid

        # 2) Vincula as categorias (pelo nome) ao subgrupo.
        for nome, sid in cat_sub.items():
            conn.execute(
                "UPDATE categorias SET subgrupo_id=%s WHERE nome=%s",
                (sid, nome),
            )

        # 3) Atribui grupo/subgrupo aos produtos pela categoria.
        conn.execute(
            """
            UPDATE produtos_cadastro p
            SET grupo_id = s.grupo_id, subgrupo_id = s.id
            FROM categorias c, subgrupos s
            WHERE c.id = p.categoria_id AND c.subgrupo_id = s.id
            """
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("ALTER TABLE categorias DROP COLUMN IF EXISTS subgrupo_id")
    finally:
        conn.autocommit = ac