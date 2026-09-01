"""CRM e comissões (POS-004/POS-005): oportunidade/obra com próxima ação e
motivo de perda; comissão por venda com política congelada e reversão por
estorno/devolução.
"""

from __future__ import annotations

from catalog_server.db import system_conn


# ─── POS-004: CRM / oportunidade ───────────────────────────

_ETAPAS = ("prospeccao", "qualificacao", "proposta", "negociacao", "fechada")


def criar_oportunidade(cliente_id: int | None, vendedor_id: int | None, titulo: str, valor: float,
                       etapa: str = "prospeccao", proxima_acao: str | None = None,
                       proximo_contato: str | None = None) -> dict:
    titulo = (titulo or "").strip()
    if not titulo:
        raise ValueError("titulo é obrigatório")
    etapa = (etapa or "prospeccao").strip().lower()
    if etapa not in _ETAPAS:
        raise ValueError("etapa inválida")
    with system_conn() as conn:
        op_id = conn.execute(
            "INSERT INTO oportunidade (cliente_id, vendedor_id, titulo, valor, etapa, proxima_acao, proximo_contato)"
            " VALUES (?,?,?,?,?,?,?) RETURNING id",
            (cliente_id, vendedor_id, titulo, float(valor or 0), etapa,
             (proxima_acao or "").strip() or None, proximo_contato),
        ).fetchone()["id"]
    return {"id": op_id, "status": "aberta"}


def atualizar_oportunidade(op_id: int, status: str, motivo_perda: str | None = None,
                           proxima_acao: str | None = None) -> dict:
    status = (status or "").strip().lower()
    if status not in ("aberta", "perdida", "ganha"):
        raise ValueError("status inválido")
    if status == "perdida" and not (motivo_perda or "").strip():
        raise ValueError("motivo de perda é obrigatório")
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE oportunidade SET status=?, motivo_perda=?, proxima_acao=? WHERE id=?",
            (status, (motivo_perda or "").strip() or None, (proxima_acao or "").strip() or None, op_id),
        )
        if cur.rowcount == 0:
            raise LookupError("Oportunidade não encontrada")
    return {"id": op_id, "status": status}


def listar_oportunidades(vendedor_id: int | None = None, status: str | None = None) -> list[dict]:
    sql = (
        "SELECT o.*, c.nome AS cliente, u.nome AS vendedor"
        " FROM oportunidade o"
        " LEFT JOIN clientes c ON c.id=o.cliente_id"
        " LEFT JOIN usuarios u ON u.id=o.vendedor_id"
    )
    args: list = []
    where: list[str] = []
    if vendedor_id:
        where.append("o.vendedor_id=?")
        args.append(vendedor_id)
    if status:
        where.append("o.status=?")
        args.append(status)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY o.id DESC LIMIT 200"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


# ─── POS-005: Comissões ────────────────────────────────────

def _percentual_vendedor(conn, vendedor_id: int) -> tuple[float, int]:
    """Política versionada de comissão (% da venda líquida, DECISAO-006)."""
    row = conn.execute(
        "SELECT percentual, versao FROM comissao_politica WHERE vendedor_id=? ORDER BY versao DESC LIMIT 1",
        (vendedor_id,),
    ).fetchone()
    if row:
        return float(row["percentual"] or 0), int(row["versao"] or 1)
    return 0.0, 1


def apurar_venda(orcamento_id: int, vendedor_id: int | None = None) -> dict:
    """Calcula e grava a comissão da venda (base = venda líquida; congelada)."""
    with system_conn() as conn:
        orc = conn.execute("SELECT * FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone()
        if not orc:
            raise LookupError("Orçamento não encontrado")
        if orc["status"] not in ("finalizado", "recebido"):
            raise ValueError(f"Orçamento {orc['status']} — comissão exige venda concluída")
        vid = vendedor_id or orc["usuario_id"]
        if not vid:
            return {"orcamento_id": orcamento_id, "comissao": 0.0, "motivo": "sem vendedor"}
        pct, versao = _percentual_vendedor(conn, vid)
        base = round(float(orc["total"] or 0) - float(orc["desconto"] or 0), 2)
        valor = round(base * pct / 100.0, 2)
        com_id = conn.execute(
            "INSERT INTO comissao (orcamento_id, vendedor_id, base, percentual, valor, politica_versao, status)"
            " VALUES (?,?,?,?,?,?, 'pendente') ON CONFLICT (orcamento_id, vendedor_id) DO NOTHING RETURNING id",
            (orcamento_id, vid, base, pct, valor, versao),
        ).fetchone()
        com_id = com_id["id"] if com_id else conn.execute(
            "SELECT id FROM comissao WHERE orcamento_id=? AND vendedor_id=?", (orcamento_id, vid)
        ).fetchone()["id"]
    return {"orcamento_id": orcamento_id, "vendedor_id": vid, "base": base, "percentual": pct,
            "valor": valor, "comissao_id": com_id}


def reverter(orcamento_id: int, motivo_origem: str = "estorno") -> dict:
    """Estorno/devolução gera reversão (não edição retroativa)."""
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM comissao WHERE orcamento_id=? AND status='pendente'",
            (orcamento_id,),
        ).fetchall()
        for r in rows:
            conn.execute(
                "UPDATE comissao SET status='revertida', revertida_de=? WHERE id=?",
                (orcamento_id, r["id"]),
            )
    return {"revertidas": len(rows)}


def listar_comissoes(status: str | None = None) -> list[dict]:
    sql = (
        "SELECT c.*, o.numero AS venda, o.cliente, u.nome AS vendedor"
        " FROM comissao c"
        " JOIN orcamentos o ON o.id=c.orcamento_id"
        " LEFT JOIN usuarios u ON u.id=c.vendedor_id"
    )
    args: list = []
    if status:
        sql += " WHERE c.status=?"
        args.append(status)
    sql += " ORDER BY c.id DESC LIMIT 200"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]