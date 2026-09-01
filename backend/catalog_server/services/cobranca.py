"""Cobrança e renegociação (VEN-006): juros/multa sobre parcela vencida com
política configurável e renegociação em novas parcelas preservando origem.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from catalog_server.db import system_conn


def _config() -> dict:
    with system_conn() as conn:
        row = conn.execute("SELECT juros_dia_pct, multa_pct FROM config_cobranca WHERE id=1").fetchone()
    if not row:
        return {"juros_dia_pct": 0.033, "multa_pct": 2.0}
    return {"juros_dia_pct": float(row["juros_dia_pct"]), "multa_pct": float(row["multa_pct"])}


def atualizar_config(juros_dia_pct: float, multa_pct: float) -> dict:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO config_cobranca (id, juros_dia_pct, multa_pct, atualizado_em)"
            " VALUES (1,?,?,NOW()) ON CONFLICT (id) DO UPDATE SET"
            " juros_dia_pct=EXCLUDED.juros_dia_pct, multa_pct=EXCLUDED.multa_pct, atualizado_em=NOW()",
            (juros_dia_pct, multa_pct),
        )
    return _config()


def _dias_atraso(vencimento: str | date) -> int:
    v = vencimento if isinstance(vencimento, date) else date.fromisoformat(str(vencimento)[:10])
    return max(0, (date.today() - v).days)


def calcular_cobranca(conta_id: int) -> dict:
    """Recalcula juros/multa da parcela vencida conforme a política."""
    cfg = _config()
    with system_conn() as conn:
        conta = conn.execute("SELECT * FROM contas_receber WHERE id=?", (conta_id,)).fetchone()
        if not conta:
            raise LookupError("Conta não encontrada")
        if conta["status"] == "pago":
            raise ValueError("Conta paga não recebe cobrança")
        saldo = float(conta["saldo"] or 0)
        dias = _dias_atraso(conta["data_vencimento"])
        juros = round(saldo * (cfg["juros_dia_pct"] / 100.0) * dias, 2) if dias > 0 else 0.0
        multa = round(saldo * (cfg["multa_pct"] / 100.0), 2) if dias > 0 else 0.0
        total_cobranca = round(juros + multa, 2)
        conn.execute(
            "UPDATE contas_receber SET juros_multa=?, cobranca_recalculada_em=NOW() WHERE id=?",
            (total_cobranca, conta_id),
        )
    return {"conta_id": conta_id, "vencimento": str(conta["data_vencimento"])[:10],
            "dias_atraso": dias, "saldo": saldo, "juros": juros, "multa": multa,
            "juros_multa_total": total_cobranca}


def renegociar(conta_id: int, novas_parcelas: list[dict], motivo: str | None = None) -> dict:
    """Renegocia: cancela a conta original e gera novas parcelas (origem
    renegociacao) com os novos vencimentos; juros/multa incorporados."""
    motivo = (motivo or "").strip() or "renegociação"
    if not novas_parcelas:
        raise ValueError("novas_parcelas é obrigatório")
    with system_conn() as conn:
        conta = conn.execute("SELECT * FROM contas_receber WHERE id=?", (conta_id,)).fetchone()
        if not conta:
            raise LookupError("Conta não encontrada")
        if conta["status"] in ("pago", "cancelado", "renegociada"):
            raise ValueError(f"Conta {conta['status']} não pode ser renegociada")
        saldo = float(conta["saldo"] or 0)
        calc = calcular_cobranca(conta_id)
        valor_renegociado = saldo + calc["juros_multa_total"]
        conn.execute(
            "UPDATE contas_receber SET status='renegociada', observacao=COALESCE(observacao,'') || ' | renegociada: ' || ? WHERE id=?",
            (motivo, conta_id),
        )
        novos = []
        total_pct = sum(float(p.get("valor_pct") or 0) for p in novas_parcelas)
        ajuste = 0.0
        for i, p in enumerate(novas_parcelas, start=1):
            dias = int(p.get("dias") or 30)
            pct = float(p.get("valor_pct") or 0)
            valor_parcela = round(valor_renegociado * pct / 100.0, 2) if pct else 0.0
            if i == len(novas_parcelas) and total_pct != 100.0:
                valor_parcela = round(valor_renegociado - ajuste, 2)  # última ajusta
            venc = (date.today() + timedelta(days=dias)).isoformat()
            novo_id = conn.execute(
                "INSERT INTO contas_receber (cliente, cliente_id, descricao, valor, saldo, data_vencimento,"
                " data_emissao, status, origem_tipo, origem_id, renegociada_de, parcela, total_parcelas)"
                " VALUES (?,?,?,?,?,?,?, 'aberto', 'renegociacao', ?, ?, ?, ?) RETURNING id",
                (conta["cliente"], conta["cliente_id"], f"{conta['descricao']} (renegociada)",
                 valor_parcela, valor_parcela, venc, date.today().isoformat(),
                 conta_id, conta_id, i, len(novas_parcelas)),
            ).fetchone()["id"]
            ajuste += valor_parcela
            novos.append(novo_id)
    return {"conta_origem": conta_id, "novas_contas": novos,
            "valor_renegociado": round(valor_renegociado, 2), "juros_multa": calc["juros_multa_total"]}


def listar_vencidas(cliente_id: int | None = None) -> list[dict]:
    sql = (
        "SELECT c.*, COALESCE(c.saldo,0) + COALESCE(c.juros_multa,0) AS valor_cobrar"
        " FROM contas_receber c WHERE c.status='aberto' AND c.data_vencimento::date < CURRENT_DATE"
    )
    args: list = []
    if cliente_id:
        sql += " AND c.cliente_id=?"
        args.append(cliente_id)
    sql += " ORDER BY c.data_vencimento"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]