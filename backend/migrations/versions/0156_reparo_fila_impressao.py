"""Migração 0156 - materializa a fila de impressao em bancos existentes.

A tabela fazia parte do snapshot SQL do baseline, mas nao possuia uma
migracao incremental propria. Bancos que aplicaram uma versao antiga do
baseline nao recebem alteracoes posteriores nesse snapshot.
"""
from __future__ import annotations

VERSION = 156
RISCO = "rotina"
NAME = "reparo_fila_impressao"

MUDANCA = {
    "o_que": [
        "Cria impressao_config e impressao_fila quando ausentes",
        "Garante as colunas e o indice usados pelo worker de impressao",
    ],
    "porque": [
        "Bancos migrados por um baseline antigo podem nao possuir a fila",
        "A ausencia da tabela encerrava o consumidor de impressao no startup",
    ],
}

_COLUNAS_CONFIG = {
    "id", "driver", "host", "porta", "papel_mm", "auto_impressao",
    "ativo", "atualizado_em",
}
_COLUNAS_FILA = {
    "id", "tipo", "referencia", "payload", "status", "erro",
    "criado_em", "processado_em",
}


def _colunas(conn, tabela: str) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s",
            (tabela,),
        ).fetchall()
    }


def guard(conn) -> bool:
    indice = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' "
        "AND tablename='impressao_fila' "
        "AND indexname='idx_impressao_fila_status'"
    ).fetchone()
    return (
        _COLUNAS_CONFIG.issubset(_colunas(conn, "impressao_config"))
        and _COLUNAS_FILA.issubset(_colunas(conn, "impressao_fila"))
        and bool(indice)
    )


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS impressao_config (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          driver TEXT NOT NULL DEFAULT 'escpos_tcp',
          host TEXT NOT NULL DEFAULT '127.0.0.1',
          porta INTEGER NOT NULL DEFAULT 9100,
          papel_mm INTEGER NOT NULL DEFAULT 80,
          auto_impressao INTEGER NOT NULL DEFAULT 0,
          ativo INTEGER NOT NULL DEFAULT 1,
          atualizado_em TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS impressao_fila (
          id BIGSERIAL PRIMARY KEY,
          tipo TEXT NOT NULL DEFAULT 'orcamento',
          referencia TEXT NOT NULL DEFAULT '',
          payload TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pendente',
          erro TEXT,
          criado_em TEXT NOT NULL DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')),
          processado_em TEXT
        )
        """
    )

    # Tambem corrige estruturas parciais sem apagar jobs/configuracoes.
    conn.execute(
        "ALTER TABLE impressao_config "
        "ADD COLUMN IF NOT EXISTS driver TEXT NOT NULL DEFAULT 'escpos_tcp', "
        "ADD COLUMN IF NOT EXISTS host TEXT NOT NULL DEFAULT '127.0.0.1', "
        "ADD COLUMN IF NOT EXISTS porta INTEGER NOT NULL DEFAULT 9100, "
        "ADD COLUMN IF NOT EXISTS papel_mm INTEGER NOT NULL DEFAULT 80, "
        "ADD COLUMN IF NOT EXISTS auto_impressao INTEGER NOT NULL DEFAULT 0, "
        "ADD COLUMN IF NOT EXISTS ativo INTEGER NOT NULL DEFAULT 1, "
        "ADD COLUMN IF NOT EXISTS atualizado_em TEXT"
    )
    conn.execute(
        "ALTER TABLE impressao_fila "
        "ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'orcamento', "
        "ADD COLUMN IF NOT EXISTS referencia TEXT NOT NULL DEFAULT '', "
        "ADD COLUMN IF NOT EXISTS payload TEXT NOT NULL DEFAULT '{}', "
        "ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pendente', "
        "ADD COLUMN IF NOT EXISTS erro TEXT, "
        "ADD COLUMN IF NOT EXISTS criado_em TEXT NOT NULL "
        "DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS')), "
        "ADD COLUMN IF NOT EXISTS processado_em TEXT"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_impressao_fila_status "
        "ON impressao_fila(status)"
    )
    conn.commit()


def backward(conn) -> None:
    # Reparo de drift: nao e seguro remover tabelas que podem ser anteriores a
    # esta migration e conter configuracoes ou documentos do operador.
    conn.commit()
