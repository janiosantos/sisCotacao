"""Migração 0108 — atributos técnicos do ramo em colunas relacionais (MDM-004)."""
from __future__ import annotations

import unicodedata

VERSION = 108
RISCO = "moderada"  # Expand: colunas novas + backfill de leitura (JSONB preservado)
NAME = "atributos_tecnicos_colunas"

MUDANCA = {
    "o_que": [
        "Promove atributos técnicos do ramo (bitola, tensão, potência, comprimento, "
        "diâmetro, rosca, material, cor, norma, validade, garantia) para colunas relacionais",
        "Backfill idempotente a partir do JSONB atributos (chaves por nome normalizado)",
        "Índices btree para filtros por bitola/cor/material/rosca",
    ],
    "porque": [
        "Filtros por atributos precisam ser indexáveis (MDM-004)",
        "O JSONB flexível permanece; as colunas são a fonte estruturada para filtro, "
        "tributação, cálculo e integração sem substituir a descrição comercial",
    ],
}

_COLUNAS = {
    "bitola": "VARCHAR(30)",
    "tensao": "VARCHAR(20)",
    "potencia": "VARCHAR(40)",
    "comprimento": "VARCHAR(40)",
    "diametro": "VARCHAR(40)",
    "rosca": "VARCHAR(40)",
    "material": "VARCHAR(80)",
    "cor": "VARCHAR(40)",
    "norma": "VARCHAR(80)",
    "validade_dias": "INTEGER",
    "garantia_dias": "INTEGER",
}

# Mapeamento de rótulo (chave do JSONB) -> coluna. Várias variantes por coluna.
_ROTULO_COLUNA: dict[str, list[str]] = {
    "bitola": ["Bitola / Tamanho", "Bitola"],
    "tensao": ["Tensão", "Tensão (V)", "Voltagem"],
    "potencia": ["Potência"],
    "comprimento": ["Comprimento"],
    "diametro": ["Diâmetro (Ø × Comprimento)", "Diâmetro", "Diâmetro (Ø)"],
    "rosca": ["Tipo de Rosca", "Rosca"],
    "material": ["Material / Tratamento", "Material"],
    "cor": ["Cor"],
    "norma": ["Norma"],
    "validade_dias": ["Validade (dias)", "Validade"],
    "garantia_dias": ["Garantia (dias)", "Garantia"],
}

_DIAS = {"validade_dias", "garantia_dias"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='produtos_cadastro' AND column_name='bitola'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    for col, tipo in _COLUNAS.items():
        conn.execute(
            f"ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS {col} {tipo}"
        )

    # Backfill idempotente a partir do JSONB atributos.
    rotulos = {_norm(r): col for col, rs in _ROTULO_COLUNA.items() for r in rs}
    rows = conn.execute(
        "SELECT id, atributos FROM produtos_cadastro "
        "WHERE atributos IS NOT NULL AND jsonb_typeof(atributos)='object'"
    ).fetchall()
    updates: dict[int, dict[str, object]] = {}
    for row in rows:
        try:
            attrs = row["atributos"]
            if not isinstance(attrs, dict):
                continue
            mapped: dict[str, object] = {}
            for chave, valor in attrs.items():
                if valor is None or valor == "":
                    continue
                col = rotulos.get(_norm(str(chave)))
                if not col:
                    continue
                texto = str(valor).strip()
                if not texto:
                    continue
                if col in _DIAS:
                    if not texto.isdigit():
                        continue
                    mapped[col] = int(texto)
                else:
                    mapped[col] = texto
            if mapped:
                updates[row["id"]] = mapped
        except (TypeError, ValueError):
            continue
    for pid, campos in updates.items():
        sets = ", ".join(f"{c}=%s" for c in campos)
        conn.execute(
            f"UPDATE produtos_cadastro SET {sets} WHERE id=%s",
            (*campos.values(), pid),
        )

    for col in ("bitola", "cor", "material", "rosca"):
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_produtos_{col} ON produtos_cadastro ({col})"
        )
    conn.commit()


def backward(conn) -> None:
    for col in _COLUNAS:
        conn.execute(f"ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS {col}")