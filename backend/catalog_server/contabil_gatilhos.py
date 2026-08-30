"""Gatilhos contábeis configuráveis por evento (AGENT-produtos P4, v2.15.0).

Conecta eventos de negócio ao `contabil.lancar()` usando as contas de
débito/crédito configuradas em `contabil_gatilho`. Idempotência preservada pelo
`lancar()` (mesma `idempotency_key` ignora retrida).
"""
from __future__ import annotations

from catalog_server.db import system_conn

EVENTOS_SUPORTADOS = ("venda_autorizada", "compra", "ajuste")

_DESCRICOES = {
    "venda_autorizada": "Venda autorizada/faturada",
    "compra": "Compra / pedido de compra",
    "ajuste": "Ajuste de estoque",
}


def listar_gatilhos() -> list[dict]:
    """Lista os gatilhos configurados (todos os suportados, com contas)."""
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT g.evento_tipo, g.ativo, g.debito_conta_id, g.credito_conta_id,"
            " g.descricao,"
            " COALESCE(d.codigo,'') AS debito_codigo, COALESCE(d.nome,'') AS debito_nome,"
            " COALESCE(c.codigo,'') AS credito_codigo, COALESCE(c.nome,'') AS credito_nome"
            " FROM contabil_gatilho g"
            " LEFT JOIN plano_de_contas d ON d.id = g.debito_conta_id"
            " LEFT JOIN plano_de_contas c ON c.id = g.credito_conta_id"
            " ORDER BY g.evento_tipo"
        ).fetchall()
    return [dict(r) for r in rows]


def configurar(
    evento_tipo: str,
    *,
    debito_conta_id: int | None,
    credito_conta_id: int | None,
    ativo: bool,
    descricao: str = "",
) -> dict:
    """Grava (ou atualiza) a configuração de um gatilho."""
    if evento_tipo not in EVENTOS_SUPORTADOS:
        raise ValueError(f"evento_tipo inválido: {evento_tipo} (use {EVENTOS_SUPORTADOS})")
    if ativo and not (debito_conta_id and credito_conta_id):
        raise ValueError("Gatilho ativo exige contas de débito e crédito")
    descricao = descricao.strip() or _DESCRICOES.get(evento_tipo, "")
    with system_conn() as conn:
        conn.execute(
            """
            INSERT INTO contabil_gatilho
                (evento_tipo, ativo, debito_conta_id, credito_conta_id, descricao)
            VALUES (?,?,?,?,?)
            ON CONFLICT (evento_tipo) DO UPDATE SET
                ativo=EXCLUDED.ativo,
                debito_conta_id=EXCLUDED.debito_conta_id,
                credito_conta_id=EXCLUDED.credito_conta_id,
                descricao=EXCLUDED.descricao,
                atualizado_em=now()
            """,
            (evento_tipo, 1 if ativo else 0, debito_conta_id, credito_conta_id, descricao),
        )
        conn.commit()
    return {
        "evento_tipo": evento_tipo,
        "ativo": ativo,
        "debito_conta_id": debito_conta_id,
        "credito_conta_id": credito_conta_id,
        "descricao": descricao,
    }


def gatilho(evento_tipo: str) -> dict | None:
    """Configuração ativa de um evento (None quando inativo)."""
    with system_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contabil_gatilho WHERE evento_tipo=?",
            (evento_tipo,),
        ).fetchone()
        if row is None or not row["ativo"]:
            return None
        d = dict(row)
        if not d.get("debito_conta_id") or not d.get("credito_conta_id"):
            return None
        return d


def disparar(
    evento_tipo: str,
    *,
    evento_id: int,
    valor: str | float,
    historico: str = "",
    periodo_competencia: str = "",
    origem_tipo: str = "",
    _conn=None,
) -> bool:
    """Dispara o gatilho de um evento (se configurado e ativo).

    Retorna False quando não há gatilho ativo (evento sem lançamento contábil
    é o comportamento esperado por padrão).
    """
    cfg = gatilho(evento_tipo)
    if cfg is None:
        return False
    from catalog_server.contabil import lancar

    return lancar(
        evento_tipo=evento_tipo,
        evento_id=evento_id,
        idempotency_key=f"{evento_tipo}-{evento_id}",
        debito_conta_id=cfg["debito_conta_id"],
        credito_conta_id=cfg["credito_conta_id"],
        valor=valor,
        historico=historico,
        periodo_competencia=periodo_competencia,
        origem_tipo=origem_tipo,
        _conn=_conn,
    )


def listar_lancamentos(limite: int = 100) -> list[dict]:
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM lancamento_contabil ORDER BY id DESC LIMIT ?",
            (max(1, min(limite, 500)),),
        ).fetchall()
        return [dict(r) for r in rows]


__all__ = [
    "EVENTOS_SUPORTADOS",
    "listar_gatilhos",
    "configurar",
    "disparar",
    "listar_lancamentos",
]
