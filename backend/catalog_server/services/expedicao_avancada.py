"""Transporte e entrega (INT-005): transportadora, SLA, eventos logísticos e
status separado do fiscal/financeiro. Entrega parcial é possível.
"""

from __future__ import annotations

from datetime import date, timedelta

from catalog_server.db import system_conn

_ESTADOS_LOGISTICOS = ("pendente", "planejada", "separada", "enviada", "parcialmente_entregue", "entregue", "cancelada")
_TRANSICOES: dict[str, set[str]] = {
    "pendente": {"planejada", "separada", "cancelada"},
    "planejada": {"separada", "cancelada"},
    "separada": {"enviada", "cancelada"},
    "enviada": {"parcialmente_entregue", "entregue"},
    "parcialmente_entregue": {"parcialmente_entregue", "entregue"},
    "entregue": set(),
    "cancelada": set(),
}


def criar_transportadora(nome: str, cnpj: str | None = None, telefone: str | None = None,
                         prazo_medio_dias: int | None = None) -> int:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("nome é obrigatório")
    with system_conn() as conn:
        return conn.execute(
            "INSERT INTO transportadora (nome, cnpj, telefone, prazo_medio_dias) VALUES (?,?,?,?) RETURNING id",
            (nome, (cnpj or "").strip() or None, (telefone or "").strip() or None, prazo_medio_dias),
        ).fetchone()["id"]


def definir_transporte(expedicao_id: int, transportadora_id: int | None = None, sla_dias: int | None = None,
                       rastreio: str | None = None) -> dict:
    """Define transportadora e SLA na expedição (SLA = hoje + prazo médio da transportadora)."""
    with system_conn() as conn:
        exp = conn.execute("SELECT * FROM expedicao WHERE id=?", (expedicao_id,)).fetchone()
        if not exp:
            raise LookupError("Expedição não encontrada")
        prazo = sla_dias
        if transportadora_id and sla_dias is None:
            tr = conn.execute("SELECT prazo_medio_dias FROM transportadora WHERE id=?", (transportadora_id,)).fetchone()
            prazo = int(tr["prazo_medio_dias"]) if tr and tr["prazo_medio_dias"] else None
        sla = (date.today() + timedelta(days=prazo)).isoformat() if prazo else None
        conn.execute(
            "UPDATE expedicao SET transportadora_id=?, sla_data=?, rastreio=? WHERE id=?",
            (transportadora_id, sla, (rastreio or "").strip() or None, expedicao_id),
        )
        _evento(conn, expedicao_id, "transporte_definido",
                f"transportadora #{transportadora_id}, SLA {sla}" if sla else "sem SLA")
    return {"expedicao_id": expedicao_id, "transportadora_id": transportadora_id, "sla_data": sla}


def _evento(conn, expedicao_id: int, evento: str, descricao: str | None = None, responsavel_id: int | None = None) -> None:
    conn.execute(
        "INSERT INTO expedicao_evento (expedicao_id, evento, descricao, responsavel_id) VALUES (?,?,?,?)",
        (expedicao_id, evento, descricao, responsavel_id),
    )


def transicionar(expedicao_id: int, novo_status: str, responsavel_id: int | None = None,
                 rastreio: str | None = None) -> dict:
    novo_status = (novo_status or "").strip().lower()
    if novo_status not in _ESTADOS_LOGISTICOS:
        raise ValueError("status logístico inválido")
    with system_conn() as conn:
        exp = conn.execute("SELECT * FROM expedicao WHERE id=?", (expedicao_id,)).fetchone()
        if not exp:
            raise LookupError("Expedição não encontrada")
        atual = exp["status"]
        if novo_status not in _TRANSICOES.get(atual, set()):
            raise ValueError(f"Transição inválida: {atual} → {novo_status}")
        campos = "status=?"
        args: list = [novo_status]
        if novo_status == "enviada":
            campos += ", data_envio=NOW()"
        if novo_status == "entregue":
            campos += ", data_entrega=NOW()"
        if rastreio:
            campos += ", rastreio=?"
            args.append(rastreio)
        args.append(expedicao_id)
        conn.execute(f"UPDATE expedicao SET {campos} WHERE id=?", tuple(args))
        _evento(conn, expedicao_id, novo_status, f"de {atual} para {novo_status}", responsavel_id)
    return {"expedicao_id": expedicao_id, "de": atual, "para": novo_status}


def listar_eventos(expedicao_id: int) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT e.*, u.nome AS responsavel_nome FROM expedicao_evento e"
            " LEFT JOIN usuarios u ON u.id=e.responsavel_id WHERE e.expedicao_id=? ORDER BY e.id",
            (expedicao_id,),
        ).fetchall()]


def listar_transportadoras(ativo: bool | None = None) -> list[dict]:
    sql = "SELECT * FROM transportadora"
    args: list = []
    if ativo is not None:
        sql += " WHERE ativo=?"
        args.append(1 if ativo else 0)
    sql += " ORDER BY nome"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]