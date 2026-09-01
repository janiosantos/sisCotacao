"""Migração 0118 — XYZ e matriz de política: variabilidade/intermitência da demanda (COM-002)."""
from __future__ import annotations

VERSION = 118
RISCO = "baixa"  # Expand: colunas novas + tabela de configuração
NAME = "xyz_politica"

MUDANCA = {
    "o_que": [
        "produtos_cadastro + classe_xyz (X/Y/Z), cv_demanda (coeficiente de variação) e intermitente",
        "xyz_config: limiares configuráveis (cv_x, cv_y, intermitência) — auditados",
        "Matriz ABC×XYZ → política recomendada (contagem, serviço, estoque)",
    ],
    "porque": [
        "Item com alta margem e demanda irregular não recebe política automática indevida (COM-002)",
        "Parâmetros e limiares são configuráveis e auditados",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='produtos_cadastro' AND column_name='classe_xyz'"
    ).fetchone()
    return bool(row)


def forward(conn) -> None:
    conn.execute("ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS classe_xyz VARCHAR(1)")
    conn.execute("ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS cv_demanda NUMERIC(10,4)")
    conn.execute("ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS intermitente BOOLEAN NOT NULL DEFAULT FALSE")
    conn.execute("ALTER TABLE produtos_cadastro ADD COLUMN IF NOT EXISTS xyz_calculado_em TIMESTAMPTZ")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS xyz_config (
            id INTEGER PRIMARY KEY,
            cv_x NUMERIC(8,4) NOT NULL DEFAULT 0.5,
            cv_y NUMERIC(8,4) NOT NULL DEFAULT 1.0,
            meses_historico INTEGER NOT NULL DEFAULT 6,
            intermitente_zeros_pct NUMERIC(8,4) NOT NULL DEFAULT 0.5,
            atualizado_por INTEGER,
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        "INSERT INTO xyz_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
    )
    conn.commit()


def backward(conn) -> None:
    for col in ("classe_xyz", "cv_demanda", "intermitente", "xyz_calculado_em"):
        conn.execute(f"ALTER TABLE produtos_cadastro DROP COLUMN IF EXISTS {col}")
    conn.execute("DROP TABLE IF EXISTS xyz_config")