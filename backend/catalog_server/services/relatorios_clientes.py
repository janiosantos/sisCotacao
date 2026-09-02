"""Relatórios comerciais de clientes e histórico de compras.

As consultas deste módulo são somente leitura. Regras de período, paginação e
ordenação ficam aqui para que tela, impressão e exportação usem exatamente os
mesmos fatos e o mesmo contrato.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Mapping

from catalog_server.db import system_conn


class RelatorioFiltroError(ValueError):
    """Filtro de relatório inválido ou fora dos limites operacionais."""


def _date(value: str | None, field: str) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise RelatorioFiltroError(f"{field} deve estar no formato AAAA-MM-DD") from exc
    return text


def _bool(value: str | bool | None, default: bool | None = None) -> bool | None:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).lower().strip()
    if text in {"1", "true", "sim", "s"}:
        return True
    if text in {"0", "false", "nao", "não", "n"}:
        return False
    raise RelatorioFiltroError("ativo deve ser true ou false")


def _limit(value) -> int:
    try:
        limit = int(value or 50)
    except (TypeError, ValueError) as exc:
        raise RelatorioFiltroError("limit deve ser um número inteiro") from exc
    if limit < 1 or limit > 200:
        raise RelatorioFiltroError("limit deve estar entre 1 e 200")
    return limit


def _offset(value) -> int:
    try:
        offset = int(value or 0)
    except (TypeError, ValueError) as exc:
        raise RelatorioFiltroError("offset deve ser um número inteiro") from exc
    if offset < 0 or offset > 1_000_000:
        raise RelatorioFiltroError("offset fora do limite permitido")
    return offset


def _base_periodo(filters: Mapping[str, object]) -> tuple[str, str]:
    inicio = _date(filters.get("data_inicio"), "data_inicio")
    fim = _date(filters.get("data_fim"), "data_fim")
    if inicio is None and fim is None:
        fim = date.today().isoformat()
        inicio = (date.today() - timedelta(days=365)).isoformat()
    elif inicio is None:
        inicio = (date.fromisoformat(fim) - timedelta(days=365)).isoformat()
    elif fim is None:
        fim = date.today().isoformat()
    if inicio > fim:
        raise RelatorioFiltroError("data_inicio não pode ser maior que data_fim")
    if date.fromisoformat(fim) - date.fromisoformat(inicio) > timedelta(days=3660):
        raise RelatorioFiltroError("O período máximo do relatório é de 10 anos")
    return inicio, fim


def _iso(value) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _masked_doc(value: str | None) -> str | None:
    text = "".join(ch for ch in str(value or "") if ch.isalnum())
    if len(text) == 11:
        return f"{text[:3]}.***.***-{text[-2:]}"
    if len(text) == 14:
        return f"{text[:2]}.***.***/****-{text[-2:]}"
    return None if not text else "***"


def _filters_clientes(filters: Mapping[str, object]) -> tuple[str, list[object], str, str]:
    where = ["1=1"]
    args: list[object] = []
    tipo = str(filters.get("tipo_pessoa") or "").strip().lower()
    if tipo:
        if tipo not in {"f", "j"}:
            raise RelatorioFiltroError("tipo_pessoa deve ser f ou j")
        where.append("LOWER(c.tipo_pessoa)=?")
        args.append(tipo)
    for field in ("segmento", "categoria", "uf", "cidade"):
        value = str(filters.get(field) or "").strip()
        if value:
            where.append(f"LOWER(c.{field})=LOWER(?)")
            args.append(value)
    ativo = _bool(filters.get("ativo"), True)
    if ativo is not None:
        where.append("c.ativo=?")
        args.append(int(ativo))
    termo = str(filters.get("q") or "").strip()
    if termo:
        like = f"%{termo}%"
        where.append("(c.nome ILIKE ? OR COALESCE(c.doc,'') ILIKE ? OR COALESCE(c.email,'') ILIKE ?)")
        args.extend([like, like, like])
    nascimento_inicio = _date(filters.get("aniversario_inicio"), "aniversario_inicio")
    nascimento_fim = _date(filters.get("aniversario_fim"), "aniversario_fim")
    if nascimento_inicio or nascimento_fim:
        start = (nascimento_inicio or nascimento_fim)[5:]
        end = (nascimento_fim or nascimento_inicio)[5:]
        if start <= end:
            where.append("TO_CHAR(c.data_nascimento, 'MM-DD') BETWEEN ? AND ?")
        else:
            where.append("(TO_CHAR(c.data_nascimento, 'MM-DD') >= ? OR TO_CHAR(c.data_nascimento, 'MM-DD') <= ?)")
        args.extend([start, end])
    ultima_inicio = _date(filters.get("ultima_compra_inicio"), "ultima_compra_inicio")
    ultima_fim = _date(filters.get("ultima_compra_fim"), "ultima_compra_fim")
    if ultima_inicio:
        where.append("COALESCE(uc.ultima_compra, '1900-01-01') >= ?")
        args.append(ultima_inicio)
    if ultima_fim:
        where.append("COALESCE(uc.ultima_compra, '1900-01-01') <= ?")
        args.append(ultima_fim)
    sem_compra = filters.get("sem_compra_dias")
    if sem_compra not in (None, ""):
        try:
            dias = int(sem_compra)
        except (TypeError, ValueError) as exc:
            raise RelatorioFiltroError("sem_compra_dias deve ser inteiro") from exc
        if dias < 1 or dias > 3650:
            raise RelatorioFiltroError("sem_compra_dias deve estar entre 1 e 3650")
        cutoff = (date.today() - timedelta(days=dias)).isoformat()
        where.append("COALESCE(uc.ultima_compra, '1900-01-01') <= ?")
        args.append(cutoff)
    order_map = {
        "nome": "LOWER(c.nome)",
        "ultima_compra": "uc.ultima_compra",
        "criado_em": "c.criado_em",
        "segmento": "LOWER(c.segmento)",
        "data_nascimento": "TO_CHAR(c.data_nascimento, 'MM-DD')",
    }
    order = order_map.get(str(filters.get("sort") or "nome"), "LOWER(c.nome)")
    direction = "DESC" if str(filters.get("dir") or "asc").lower() == "desc" else "ASC"
    return " AND ".join(where), args, order, direction


def clientes(filters: Mapping[str, object] | None = None) -> dict:
    filters = filters or {}
    inicio, fim = _base_periodo(filters)
    limit = _limit(filters.get("limit"))
    offset = _offset(filters.get("offset"))
    where, args, order, direction = _filters_clientes(filters)
    joins = (
        " FROM clientes c LEFT JOIN vendedores v ON v.id=c.vendedor_id "
        " LEFT JOIN (SELECT cliente_id, MAX(SUBSTR(criado_em,1,10)) AS ultima_compra "
        " FROM orcamentos WHERE status IN ('finalizado','recebido') AND cliente_id IS NOT NULL "
        " GROUP BY cliente_id) uc ON uc.cliente_id=c.id"
    )
    sql = (
        "SELECT c.id, c.nome, c.tipo_pessoa, c.doc, c.email, c.telefone, c.whatsapp, "
        "c.cidade, c.uf, c.segmento, c.categoria, c.ativo, c.criado_em, "
        "c.data_nascimento, c.canal_preferencial, c.consentimento_contato, "
        "v.nome AS vendedor_nome, uc.ultima_compra" + joins +
        " WHERE " + where + f" ORDER BY {order} {direction}, c.id ASC LIMIT ? OFFSET ?"
    )
    count_sql = "SELECT COUNT(*) AS total" + joins + " WHERE " + where
    with system_conn() as conn:
        total = int(conn.execute(count_sql, tuple(args)).fetchone()["total"] or 0)
        rows = conn.execute(sql, tuple([*args, limit, offset])).fetchall()
    itens = []
    for row in rows:
        item = dict(row)
        item["doc"] = _masked_doc(item.get("doc"))
        item["data_nascimento"] = _iso(item.get("data_nascimento"))
        item["consentimento_contato"] = bool(item.get("consentimento_contato"))
        itens.append(item)
    return {
        "report_key": "clientes",
        "kind": "analitico",
        "periodo": {"inicio": inicio, "fim": fim},
        "filtros": dict(filters),
        "itens": itens,
        "paginacao": {"total": total, "limit": limit, "offset": offset, "proximo_offset": offset + limit if offset + limit < total else None},
    }


def compras_cliente(cliente_id: int, filters: Mapping[str, object] | None = None) -> dict:
    filters = filters or {}
    inicio, fim = _base_periodo(filters)
    limit = _limit(filters.get("limit"))
    offset = _offset(filters.get("offset"))
    try:
        cid = int(cliente_id)
    except (TypeError, ValueError) as exc:
        raise RelatorioFiltroError("cliente_id inválido") from exc
    with system_conn() as conn:
        cliente = conn.execute("SELECT id, nome, doc, segmento, categoria FROM clientes WHERE id=?", (cid,)).fetchone()
        if not cliente:
            raise LookupError("Cliente não encontrado")
        base = (
            " FROM orcamentos o JOIN orcamento_itens oi ON oi.orcamento_id=o.id "
            " LEFT JOIN usuarios u ON u.id=o.usuario_id "
            " WHERE o.cliente_id=? AND o.status IN ('finalizado','recebido') "
            " AND SUBSTR(o.criado_em,1,10) BETWEEN ? AND ?"
        )
        params = [cid, inicio, fim]
        total_row = conn.execute("SELECT COUNT(*) AS total" + base, tuple(params)).fetchone()
        sum_row = conn.execute(
            "SELECT COUNT(DISTINCT o.id) AS pedidos, COALESCE(SUM(oi.quantidade * oi.preco_unitario),0) AS bruto, "
            "COALESCE(SUM(oi.quantidade * oi.preco_unitario * (1 - COALESCE(oi.desconto_percentual,0)/100.0)),0) AS liquido"
            + base,
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            "SELECT o.id AS orcamento_id, o.numero, SUBSTR(o.criado_em,1,10) AS data_venda, o.status, "
            "oi.nome, oi.sku, oi.marca, oi.quantidade, oi.preco_unitario, oi.desconto_percentual, "
            "(oi.quantidade * oi.preco_unitario * (1 - COALESCE(oi.desconto_percentual,0)/100.0)) AS total_item, "
            "u.nome AS vendedor_nome" + base + " ORDER BY o.criado_em DESC, o.id DESC, oi.id ASC LIMIT ? OFFSET ?",
            tuple([*params, limit, offset]),
        ).fetchall()
    itens = [dict(row) for row in rows]
    return {
        "report_key": "clientes.compras",
        "kind": "analitico",
        "cliente": {**dict(cliente), "doc": _masked_doc(cliente["doc"])},
        "periodo": {"inicio": inicio, "fim": fim},
        "filtros": {**dict(filters), "cliente_id": cid},
        "resumo": {
            "pedidos": int(sum_row["pedidos"] or 0),
            "receita_bruta": round(float(sum_row["bruto"] or 0), 2),
            "receita_liquida": round(float(sum_row["liquido"] or 0), 2),
        },
        "itens": itens,
        "paginacao": {
            "total": int(total_row["total"] or 0),
            "limit": limit,
            "offset": offset,
            "proximo_offset": offset + limit if offset + limit < int(total_row["total"] or 0) else None,
        },
    }
