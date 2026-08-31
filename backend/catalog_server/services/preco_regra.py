"""Regras de preço por contexto e prioridade (MDM-007).

Uma regra define preço fixo ou desconto para um produto quando o contexto casa:
canal, cliente, segmento e/ou quantidade mínima. `prioridade` menor vence;
regras gerais (sem contexto) são fallback. `margem_minima_pct` alimenta a
alçada de margem (DECISAO-008: reutiliza o mecanismo de alçada de desconto).
O motor (`pricing_engine.preco_efetivo`) aplica regra → tabela → motor → base,
devolvendo a explicação da regra usada.
"""

from __future__ import annotations

from decimal import Decimal

from catalog_server.db import system_conn

_COLUNAS = (
    "id, produto_id, prioridade, canal, cliente_id, segmento, quantidade_min, "
    "preco, desconto_pct, margem_minima_pct, vigencia_inicio, vigencia_fim, "
    "motivo, ativo, versao, criado_em, atualizado_em"
)


def listar(produto_id: int) -> list[dict]:
    with system_conn() as conn:
        rows = conn.execute(
            f"SELECT {_COLUNAS} FROM preco_regra "
            "WHERE produto_id=? AND ativo ORDER BY prioridade, id",
            (produto_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def salvar(
    produto_id: int,
    prioridade: int,
    canal: str | None,
    cliente_id: int | None,
    segmento: str | None,
    quantidade_min: float | None,
    preco: float | None,
    desconto_pct: float | None,
    margem_minima_pct: float | None,
    vigencia_inicio: str | None,
    vigencia_fim: str | None,
    motivo: str | None,
    usuario_id: int | None,
) -> dict:
    preco_d = Decimal(str(preco)) if preco is not None else None
    desconto_d = Decimal(str(desconto_pct)) if desconto_pct is not None else None
    margem_d = Decimal(str(margem_minima_pct)) if margem_minima_pct is not None else None
    if preco_d is not None and preco_d < 0:
        raise ValueError("preco não pode ser negativo")
    if desconto_d is not None and not (0 <= desconto_d <= 100):
        raise ValueError("desconto_pct deve estar entre 0 e 100")
    if preco_d is None and desconto_d is None:
        raise ValueError("informe preco ou desconto_pct")
    qtd = Decimal(str(quantidade_min)) if quantidade_min is not None else None
    if qtd is not None and qtd < 0:
        raise ValueError("quantidade_min não pode ser negativa")
    with system_conn() as conn:
        novo_id = conn.execute(
            "INSERT INTO preco_regra "
            "(produto_id, prioridade, canal, cliente_id, segmento, quantidade_min, "
            "preco, desconto_pct, margem_minima_pct, vigencia_inicio, vigencia_fim, "
            "motivo, ativo, versao, criado_por) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,TRUE,1,?) RETURNING id",
            (
                produto_id,
                int(prioridade or 10),
                (canal or "").strip() or None,
                cliente_id,
                (segmento or "").strip() or None,
                qtd,
                preco_d,
                desconto_d,
                margem_d,
                vigencia_inicio or None,
                vigencia_fim or None,
                (motivo or "").strip() or None,
                usuario_id,
            ),
        ).fetchone()["id"]
        r = conn.execute(
            f"SELECT {_COLUNAS} FROM preco_regra WHERE id=?", (novo_id,)
        ).fetchone()
        return dict(r)


def excluir(produto_id: int, regra_id: int) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE preco_regra SET ativo=FALSE, atualizado_em=NOW() "
            "WHERE id=? AND produto_id=? AND ativo",
            (regra_id, produto_id),
        )
        return cur.rowcount > 0


def resolver(
    produto_id: int,
    canal: str | None = None,
    cliente_id: int | None = None,
    segmento: str | None = None,
    quantidade: float | None = None,
) -> dict | None:
    """Retorna a regra ativa de maior prioridade cujo contexto casa (ou fallback geral)."""
    with system_conn() as conn:
        rows = conn.execute(
            f"SELECT {_COLUNAS} FROM preco_regra "
            "WHERE produto_id=? AND ativo ORDER BY prioridade, id",
            (produto_id,),
        ).fetchall()
    regras = [dict(r) for r in rows]
    for r in regras:
        if r["vigencia_inicio"] and r["vigencia_inicio"] > _now():
            continue
        if r["vigencia_fim"] and r["vigencia_fim"] < _now():
            continue
        if r["canal"] and (r["canal"] != canal):
            continue
        if r["cliente_id"] and (r["cliente_id"] != cliente_id):
            continue
        if r["segmento"] and (r["segmento"] != segmento):
            continue
        if r["quantidade_min"] is not None and (quantidade is None or quantidade < float(r["quantidade_min"])):
            continue
        return r
    return None


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()