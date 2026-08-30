"""Pré-lançamentos contábeis espelho por evento (AGENT-produtos P4).

Idempotentes por `idempotency_key`: retrida do mesmo evento ignora.
"""
from __future__ import annotations

from catalog_server.db import system_conn


def lancar(
    *,
    evento_tipo: str,
    evento_id: int,
    idempotency_key: str,
    debito_conta_id: int | None,
    credito_conta_id: int | None,
    valor: str | float,
    historico: str = "",
    periodo_competencia: str = "",
    origem_tipo: str = "",
    _conn=None,
) -> bool:
    """Grava o lançamento; retorna False se já existia (idempotente)."""
    if _conn is None:
        with system_conn() as conn:
            return lancar(
                evento_tipo=evento_tipo, evento_id=evento_id,
                idempotency_key=idempotency_key, debito_conta_id=debito_conta_id,
                credito_conta_id=credito_conta_id, valor=valor, historico=historico,
                periodo_competencia=periodo_competencia, origem_tipo=origem_tipo,
                _conn=conn,
            )

    existe = _conn.execute(
        "SELECT 1 FROM lancamento_contabil WHERE idempotency_key=?",
        (idempotency_key,),
    ).fetchone()
    if existe:
        return False
    _conn.execute(
        """
        INSERT INTO lancamento_contabil (
            evento_tipo, evento_id, idempotency_key,
            debito_conta_id, credito_conta_id, valor,
            historico, periodo_competencia, origem_tipo
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            evento_tipo, evento_id, idempotency_key,
            debito_conta_id, credito_conta_id, str(valor),
            historico, periodo_competencia, origem_tipo,
        ),
    )
    return True
