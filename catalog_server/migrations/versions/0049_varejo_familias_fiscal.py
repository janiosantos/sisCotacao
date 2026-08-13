"""0049 - Varejo de construção: famílias/atributos e campos fiscais por família.

Prepara o cadastro para loja de varejo de material elétrico, hidráulica,
parafusos e ferramentas:

1. Famílias com atributos prontos para gerar variações:
   - `Material Elétrico`  (tipo, tensão, corrente, polos, cor)
   - `Hidraulica`         (tipo, material, diâmetro)
   - `Ferramentas`        (tipo, tamanho, material)
   - `Parafuso`           (só clarifica o rótulo do atributo combinado)
2. Campos fiscais/tributários:
   - `familias.ncm_padrao` e `familias.unidade_padrao` (herdados pelas novas
     variantes da família).
   - `variantes.unidade_tributavel` (unidade para NF-e; vazia = igual à
     unidade de venda).
3. NCM padrão para as famílias mais relevantes + backfill do NCM nas variantes
   existentes que ainda não têm (e em `fiscal_config`).
"""
from __future__ import annotations

import json
import sqlite3

VERSION = 49
NAME = "Varejo de construcao: familias/atributos e campos fiscais por familia"

# (nome, descricao, ncm_padrao, unidade_padrao, [(attr, tipo, [opcoes])])
_FAMILIAS = [
    (
        "Ferramentas",
        "Ferramentas manuais em geral",
        "8205.59.00",
        "UN",
        [
            ("Tipo", "lista", [
                "Chave de Fenda", "Chave Philips", "Chave Combinada",
                "Chave de Boca", "Chave Estrela", "Chave Hexagonal",
                "Alicate Universal", "Alicate de Corte", "Alicate de Bico",
                "Martelo", "Marreta", "Serrote", "Trena", "Estilete",
                "Nível", "Espátula", "Desempenadeira", "Trena a Laser",
            ]),
            ("Tamanho", "livre", []),
            ("Material", "lista", [
                "Aço Cromo Vanádio", "Aço Carbono", "Aço Inox",
                "Cabo Emborrachado", "Cabo de Madeira", "Plástico",
            ]),
        ],
    ),
    (
        "Material Elétrico",
        "Disjuntores, tomadas, interruptores, conectores e acessórios elétricos",
        "8536.69.90",
        "UN",
        [
            ("Tipo", "lista", [
                "Disjuntor", "Tomada", "Interruptor", "Conector", "Plugue",
                "Fita Isolante", "Conduíte", "Eletrocalha", "Barra de Energia",
                "Extensão", "Chuveiro", "Campainha", "Sensor de Presença",
            ]),
            ("Tensão", "lista", ["110V", "127V", "220V", "380V", "Bivolt"]),
            ("Corrente", "lista", ["10A", "16A", "20A", "25A", "32A", "40A", "63A"]),
            ("Polos", "lista", ["1 Polo", "2 Polos", "3 Polos"]),
            ("Cor", "lista", ["Branco", "Preto", "Cinza", "Marfim", "Vermelho"]),
        ],
    ),
    (
        "Hidraulica",
        "Tubos, conexões, registros, válvulas e torneiras",
        "8481.80.99",
        "UN",
        [
            ("Tipo", "lista", [
                "Tubo", "Conexão", "Joelho", "Tê", "Luva", "Registro",
                "Válvula", "Mangueira", "Torneira", "Caixa d'água",
            ]),
            ("Material", "lista", [
                "PVC", "CPVC", "Cobre", "Aço Galvanizado", "PPR", "Latão",
            ]),
            ("Diâmetro", "livre", []),
        ],
    ),
]

# NCM padrão para famílias já existentes (aplicado como sugestão inicial).
_NCM_PADRAO = {
    "Ferramentas": ("8205.59.00", "UN"),
    "Material Elétrico": ("8536.69.90", "UN"),
    "Parafuso": ("7318.14.00", "PC"),
    "Hidraulica": ("8481.80.99", "UN"),
    "Fios e Cabos": ("8544.49.00", "RL"),
    "Lâmpada": ("8539.52.00", "UN"),
    "Soquetes e Bocais": ("8536.61.00", "UN"),
    "Quadros e Caixas": ("8537.10.90", "UN"),
    "Instrumentos de Medição": ("9030.31.00", "UN"),
    "Acessórios para Ferramentas": ("8207.90.00", "UN"),
    "Fixação e Aperto": ("7326.90.90", "UN"),
    "Químicos e Adesivos": ("3506.10.90", "UN"),
    "Lubrificantes e Aerossóis": ("3403.99.00", "UN"),
    "Tubos e Conexões": ("3917.40.90", "UN"),
    "Registros e Válvulas": ("8481.80.99", "UN"),
    "Mangueiras": ("3917.39.00", "MT"),
}


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def guard(conn: sqlite3.Connection) -> bool:
    try:
        return (
            "ncm_padrao" in _cols(conn, "familias")
            and "unidade_padrao" in _cols(conn, "familias")
            and "unidade_tributavel" in _cols(conn, "variantes")
        )
    except sqlite3.OperationalError:
        return False


def _ensure_familia(conn: sqlite3.Connection, nome: str, descricao: str) -> int:
    row = conn.execute(
        "SELECT id FROM familias WHERE LOWER(nome)=LOWER(?)", (nome,)
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO familias (nome, descricao) VALUES (?,?)", (nome, descricao)
    )
    return cur.lastrowid


def _add_atributos(conn: sqlite3.Connection, familia_id: int, atributos: list) -> None:
    ordem = conn.execute(
        "SELECT COALESCE(MAX(ordem),0) FROM familia_atributos WHERE familia_id=?",
        (familia_id,),
    ).fetchone()[0]
    for i, (nome, tipo, opcoes) in enumerate(atributos, start=1):
        conn.execute(
            "INSERT OR IGNORE INTO familia_atributos"
            " (familia_id, nome, tipo, opcoes, obrigatorio, ordem)"
            " VALUES (?,?,?,?,0,?)",
            (familia_id, nome, tipo, json.dumps(opcoes, ensure_ascii=False), ordem + i),
        )


def forward(conn: sqlite3.Connection) -> None:
    # 1. Colunas fiscais.
    if "ncm_padrao" not in _cols(conn, "familias"):
        conn.execute("ALTER TABLE familias ADD COLUMN ncm_padrao TEXT DEFAULT ''")
    if "unidade_padrao" not in _cols(conn, "familias"):
        conn.execute("ALTER TABLE familias ADD COLUMN unidade_padrao TEXT DEFAULT 'UN'")
    if "unidade_tributavel" not in _cols(conn, "variantes"):
        conn.execute("ALTER TABLE variantes ADD COLUMN unidade_tributavel TEXT DEFAULT ''")

    # 2. Seed das famílias com atributos.
    for nome, descricao, ncm, unidade, atributos in _FAMILIAS:
        fid = _ensure_familia(conn, nome, descricao)
        _add_atributos(conn, fid, atributos)
        conn.execute(
            "UPDATE familias SET ncm_padrao=?, unidade_padrao=? WHERE id=?",
            (ncm, unidade, fid),
        )

    # 3. NCM padrão para famílias existentes (só preenche quando vazio).
    for nome, (ncm, unidade) in _NCM_PADRAO.items():
        conn.execute(
            "UPDATE familias SET"
            " ncm_padrao=CASE WHEN ncm_padrao='' THEN ? ELSE ncm_padrao END,"
            " unidade_padrao=CASE WHEN unidade_padrao='UN' OR unidade_padrao='' THEN ? ELSE unidade_padrao END"
            " WHERE LOWER(nome)=LOWER(?)",
            (ncm, unidade, nome),
        )

    # 4. Backfill de NCM nas variantes sem NCM (e em fiscal_config).
    for nome, (ncm, _unidade) in _NCM_PADRAO.items():
        conn.execute(
            "UPDATE variantes SET ncm=? WHERE (ncm IS NULL OR ncm='')"
            " AND produto_id IN (SELECT id FROM produtos_cadastro WHERE familia_id="
            "  (SELECT id FROM familias WHERE LOWER(nome)=LOWER(?)))",
            (ncm, nome),
        )
        conn.execute(
            "UPDATE fiscal_config SET ncm=? WHERE (ncm IS NULL OR ncm='')"
            " AND variante_id IN (SELECT v.id FROM variantes v"
            "  JOIN produtos_cadastro p ON p.id=v.produto_id"
            "  JOIN familias f ON f.id=p.familia_id WHERE LOWER(f.nome)=LOWER(?))",
            (ncm, nome),
        )

    # 5. Clarifica o rótulo do atributo combinado da família Parafuso.
    conn.execute(
        "UPDATE familia_atributos SET nome='Diâmetro (Ø × Comprimento)'"
        " WHERE nome='Diâmetro' AND familia_id="
        "  (SELECT id FROM familias WHERE LOWER(nome)=LOWER('Parafuso'))"
    )


def backward(conn: sqlite3.Connection) -> None:
    for table, col in (
        ("familias", "ncm_padrao"),
        ("familias", "unidade_padrao"),
        ("variantes", "unidade_tributavel"),
    ):
        try:
            conn.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
        except sqlite3.OperationalError:
            pass
