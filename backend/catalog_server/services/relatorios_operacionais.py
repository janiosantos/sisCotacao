"""Relatorios analiticos de vendas, compras e estoque.

As consultas partem dos documentos/fatos existentes e retornam contratos
estaveis para tela, impressao e exportacao. Nenhum filtro vira SQL livre:
dimensoes, ordenacao e limites sao listas controladas no servico.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Mapping

from catalog_server.db import system_conn


class RelatorioOperacionalError(ValueError):
    """Filtro invalido ou fora do limite operacional."""


def _periodo(filters: Mapping[str, object]) -> tuple[str, str]:
    hoje = date.today()
    inicio = str(filters.get("data_inicio") or date(hoje.year, 1, 1)).strip()
    fim = str(filters.get("data_fim") or hoje).strip()
    try:
        inicio_dt = date.fromisoformat(inicio)
        fim_dt = date.fromisoformat(fim)
    except ValueError as exc:
        raise RelatorioOperacionalError("Periodo deve usar o formato AAAA-MM-DD") from exc
    if inicio_dt > fim_dt:
        raise RelatorioOperacionalError("data_inicio nao pode ser maior que data_fim")
    if fim_dt - inicio_dt > timedelta(days=3660):
        raise RelatorioOperacionalError("O periodo maximo do relatorio e de 10 anos")
    return inicio, fim


def _int_filter(filters: Mapping[str, object], name: str) -> int | None:
    value = filters.get(name)
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RelatorioOperacionalError(f"{name} deve ser inteiro") from exc
    if parsed < 1:
        raise RelatorioOperacionalError(f"{name} deve ser positivo")
    return parsed


def _pagination(filters: Mapping[str, object]) -> tuple[int, int]:
    try:
        limit = int(filters.get("limit") or 50)
        offset = int(filters.get("offset") or 0)
    except (TypeError, ValueError) as exc:
        raise RelatorioOperacionalError("limit e offset devem ser inteiros") from exc
    if limit < 1 or limit > 200:
        raise RelatorioOperacionalError("limit deve estar entre 1 e 200")
    if offset < 0 or offset > 1_000_000:
        raise RelatorioOperacionalError("offset fora do limite permitido")
    return limit, offset


def _float(value) -> float:
    return round(float(value or 0), 2)


def _vendas_base(filters: Mapping[str, object]) -> tuple[str, list[object]]:
    where = ["1=1"]
    args: list[object] = []
    int_filters = {
        "produto_id": "l.produto_id",
        "categoria_id": "l.categoria_id",
        "vendedor_id": "l.vendedor_id",
        "cliente_id": "l.cliente_id",
        "deposito_id": "l.deposito_id",
        "condicao_pagamento_id": "l.condicao_pagamento_id",
    }
    for name, column in int_filters.items():
        value = _int_filter(filters, name)
        if value is not None:
            where.append(f"{column}=?")
            args.append(value)
    for name, column in (("marca", "l.marca"), ("segmento", "l.segmento"), ("canal", "l.canal")):
        value = str(filters.get(name) or "").strip()
        if value:
            where.append(f"LOWER(COALESCE({column},''))=LOWER(?)")
            args.append(value)
    termo = str(filters.get("q") or "").strip()
    if termo:
        like = f"%{termo}%"
        where.append("(l.produto_nome ILIKE ? OR l.sku ILIKE ? OR l.cliente_nome ILIKE ? OR l.marca ILIKE ?)")
        args.extend([like, like, like, like])
    return " AND ".join(where), args


_VENDAS_DIMENSOES = {
    "produto": ("produto_id", "produto_nome", "Produto"),
    "categoria": ("categoria_id", "categoria_nome", "Categoria"),
    "marca": ("marca", "marca", "Marca"),
    "vendedor": ("vendedor_id", "vendedor_nome", "Vendedor"),
    "cliente": ("cliente_id", "cliente_nome", "Cliente"),
    "segmento": ("segmento", "segmento", "Segmento"),
    "deposito": ("deposito_id", "deposito_nome", "Deposito"),
    "canal": ("canal", "canal", "Canal"),
    "condicao": ("condicao_pagamento_id", "condicao_nome", "Condicao de pagamento"),
}


def vendas_analitico(filters: Mapping[str, object] | None = None) -> dict:
    filters = filters or {}
    agrupamento = str(filters.get("agrupamento") or "produto").strip().lower()
    if agrupamento not in _VENDAS_DIMENSOES:
        raise RelatorioOperacionalError("agrupamento de vendas invalido")
    limit, offset = _pagination(filters)
    inicio, fim = _periodo(filters)
    where, where_args = _vendas_base(filters)
    dim_id, dim_label, dim_nome = _VENDAS_DIMENSOES[agrupamento]
    base = """
        WITH custo AS (
            SELECT origem_id AS orcamento_id, produto_id,
                   SUM(COALESCE(custo_unitario,0) * quantidade) AS cmv
            FROM estoque_movimento
            WHERE tipo='saida' AND origem_tipo='venda'
            GROUP BY origem_id, produto_id
        ), linhas AS (
            SELECT o.id AS orcamento_id, o.criado_em,
                   oi.produto_id,
                   MIN(COALESCE(p.nome, oi.nome)) AS produto_nome,
                   MIN(COALESCE(oi.sku, p.sku, '')) AS sku,
                   p.categoria_id, COALESCE(cat.nome, 'Sem categoria') AS categoria_nome,
                   COALESCE(NULLIF(oi.marca,''), p.marca, 'Sem marca') AS marca,
                   o.usuario_id AS vendedor_id, COALESCE(u.nome, 'Nao informado') AS vendedor_nome,
                   o.cliente_id, COALESCE(c.nome, o.cliente, 'Consumidor') AS cliente_nome,
                   c.segmento,
                   o.deposito_id, COALESCE(dep.nome, 'Nao informado') AS deposito_nome,
                   o.modelo_documento AS canal,
                   o.condicao_pagamento_id,
                   COALESCE(cp.nome, 'Nao informado') AS condicao_nome,
                   SUM(oi.quantidade) AS quantidade,
                   SUM(oi.quantidade * oi.preco_unitario) AS receita_bruta,
                   SUM(oi.quantidade * oi.preco_unitario * COALESCE(oi.desconto_percentual,0)/100.0) AS desconto,
                   SUM(oi.quantidade * oi.preco_unitario * (1 - COALESCE(oi.desconto_percentual,0)/100.0)) AS receita_liquida
            FROM orcamentos o
            JOIN orcamento_itens oi ON oi.orcamento_id=o.id
            LEFT JOIN produtos_cadastro p ON p.id=oi.produto_id
            LEFT JOIN categorias cat ON cat.id=p.categoria_id
            LEFT JOIN usuarios u ON u.id=o.usuario_id
            LEFT JOIN clientes c ON c.id=o.cliente_id
            LEFT JOIN depositos dep ON dep.id=o.deposito_id
            LEFT JOIN condicoes_pagamento cp ON cp.id=o.condicao_pagamento_id
            WHERE o.status IN ('finalizado','recebido')
              AND SUBSTR(o.criado_em,1,10) BETWEEN ? AND ?
            GROUP BY o.id, o.criado_em, oi.produto_id, p.categoria_id, cat.nome,
                     COALESCE(NULLIF(oi.marca,''), p.marca, 'Sem marca'),
                     o.usuario_id, u.nome, o.cliente_id, c.nome, o.cliente, c.segmento,
                     o.deposito_id, dep.nome, o.modelo_documento, o.condicao_pagamento_id, cp.nome
        ), agregado AS (
            SELECT {dim_id} AS dimensao_id, {dim_label} AS dimensao,
                   SUM(l.quantidade) AS quantidade,
                   COUNT(DISTINCT l.orcamento_id) AS pedidos,
                   COUNT(DISTINCT l.cliente_id) FILTER (WHERE l.cliente_id IS NOT NULL) AS clientes,
                   SUM(l.receita_bruta) AS receita_bruta,
                   SUM(l.desconto) AS desconto,
                   SUM(l.receita_liquida) AS receita_liquida,
                   SUM(COALESCE(c.cmv,0)) AS cmv
            FROM linhas l
            LEFT JOIN custo c ON c.orcamento_id=l.orcamento_id AND c.produto_id=l.produto_id
            WHERE {where}
            GROUP BY {dim_id}, {dim_label}
        )
    """.format(dim_id=f"l.{dim_id}", dim_label=f"l.{dim_label}", where=where)
    # Date arguments belong to the inner CTE, then filter arguments belong to
    # the aggregate query. This keeps the query plan stable.
    args = [inicio, fim, *where_args]
    order_map = {
        "dimensao": "dimensao", "quantidade": "quantidade", "pedidos": "pedidos",
        "clientes": "clientes", "receita_bruta": "receita_bruta", "desconto": "desconto",
        "receita_liquida": "receita_liquida", "cmv": "cmv", "margem": "(receita_liquida-cmv)",
    }
    order = order_map.get(str(filters.get("sort") or "receita_liquida"), "receita_liquida")
    direction = "ASC" if str(filters.get("dir") or "desc").lower() == "asc" else "DESC"
    with system_conn() as conn:
        total = int(conn.execute(f"{base} SELECT COUNT(*) AS total FROM agregado", tuple(args)).fetchone()["total"] or 0)
        summary = conn.execute(
            f"{base} SELECT COALESCE(SUM(l.quantidade),0) AS quantidade, COUNT(DISTINCT l.orcamento_id) AS pedidos, "
            "COUNT(DISTINCT l.cliente_id) FILTER (WHERE l.cliente_id IS NOT NULL) AS clientes, "
            "COALESCE(SUM(l.receita_bruta),0) AS receita_bruta, COALESCE(SUM(l.desconto),0) AS desconto, "
            "COALESCE(SUM(l.receita_liquida),0) AS receita_liquida, COALESCE(SUM(c.cmv),0) AS cmv "
            "FROM linhas l LEFT JOIN custo c ON c.orcamento_id=l.orcamento_id AND c.produto_id=l.produto_id "
            f"WHERE {where}", tuple(args),
        ).fetchone()
        rows = conn.execute(
            f"{base} SELECT dimensao_id, dimensao, quantidade, pedidos, clientes, receita_bruta, desconto, receita_liquida, cmv, "
            f"(receita_liquida-cmv) AS margem_bruta FROM agregado ORDER BY {order} {direction}, dimensao ASC LIMIT ? OFFSET ?",
            tuple([*args, limit, offset]),
        ).fetchall()
    itens = []
    for row in rows:
        item = dict(row)
        item.update({key: _float(item.get(key)) for key in ("quantidade", "receita_bruta", "desconto", "receita_liquida", "cmv", "margem_bruta")})
        item["margem_pct"] = round(item["margem_bruta"] / item["receita_liquida"] * 100, 2) if item["receita_liquida"] else 0.0
        itens.append(item)
    return {
        "report_key": "vendas.analitico", "kind": "analitico", "calculation_version": "1.0",
        "periodo": {"inicio": inicio, "fim": fim}, "agrupamento": agrupamento,
        "dimensao": dim_nome, "filtros": dict(filters), "itens": itens,
        "resumo": {key: _float(summary[key]) for key in ("quantidade", "receita_bruta", "desconto", "receita_liquida", "cmv")}
        | {"pedidos": int(summary["pedidos"] or 0), "clientes": int(summary["clientes"] or 0)},
        "paginacao": {"total": total, "limit": limit, "offset": offset, "proximo_offset": offset + limit if offset + limit < total else None},
    }


def compras_analitico(filters: Mapping[str, object] | None = None) -> dict:
    filters = filters or {}
    inicio, fim = _periodo(filters)
    limit, offset = _pagination(filters)
    where = ["data_pedido BETWEEN ? AND ?"]
    args: list[object] = [inicio, fim]
    for name, column in (("fornecedor_id", "fornecedor_id"), ("deposito_id", "deposito_id")):
        value = _int_filter(filters, name)
        if value is not None:
            where.append(f"{column}=?")
            args.append(value)
    status = str(filters.get("status") or "").strip().lower()
    if status:
        where.append("LOWER(status)=?")
        args.append(status)
    termo = str(filters.get("q") or "").strip()
    if termo:
        like = f"%{termo}%"
        where.append("(fornecedor_nome ILIKE ? OR produto_nome ILIKE ? OR sku ILIKE ? OR numero ILIKE ?)")
        args.extend([like, like, like, like])
    base = """
        WITH recebido AS (
            SELECT ri.pedido_item_id, SUM(COALESCE(ri.qtd_aceita,0)) AS quantidade_recebida
            FROM recebimento_item ri JOIN recebimento r ON r.id=ri.recebimento_id
            WHERE r.status IN ('conferido','finalizado')
            GROUP BY ri.pedido_item_id
        ), linhas AS (
            SELECT pc.id AS pedido_id, pc.numero, pc.status,
                   COALESCE(pc.data_pedido::date, pc.data_geracao::date, pc.criado_em::date) AS data_pedido,
                   pc.data_prometida::date AS data_prometida, pc.data_recebida::date AS data_recebida,
                   pc.fornecedor_id, COALESCE(f.nome,'Nao informado') AS fornecedor_nome,
                   pc.deposito_id, COALESCE(dep.nome,'Nao informado') AS deposito_nome,
                   pi.id AS pedido_item_id, ci.produto_id, COALESCE(p.nome, 'Produto nao informado') AS produto_nome,
                   COALESCE(p.sku,'') AS sku, pi.quantidade AS quantidade_pedida,
                   COALESCE(r.quantidade_recebida,0) AS quantidade_recebida,
                   pi.preco_unitario, pi.quantidade * pi.preco_unitario AS valor_pedido,
                   COALESCE(r.quantidade_recebida,0) * pi.preco_unitario AS valor_recebido
            FROM pedidos_compra pc JOIN pedido_itens pi ON pi.pedido_id=pc.id
            LEFT JOIN cotacao_itens ci ON ci.id=pi.cotacao_item_id
            LEFT JOIN produtos_cadastro p ON p.id=ci.produto_id
            LEFT JOIN fornecedores f ON f.id=pc.fornecedor_id
            LEFT JOIN depositos dep ON dep.id=pc.deposito_id
            LEFT JOIN recebido r ON r.pedido_item_id=pi.id
        )
    """
    condition = " AND ".join(where)
    query_base = f"{base} SELECT * FROM linhas WHERE {condition}"
    with system_conn() as conn:
        total = int(conn.execute(f"{base} SELECT COUNT(*) AS total FROM linhas WHERE {condition}", tuple(args)).fetchone()["total"] or 0)
        summary = conn.execute(
            f"{base} SELECT COUNT(DISTINCT pedido_id) AS pedidos, COALESCE(SUM(valor_pedido),0) AS valor_pedido, "
            "COALESCE(SUM(valor_recebido),0) AS valor_recebido, COALESCE(SUM(quantidade_pedida-quantidade_recebida),0) AS quantidade_pendente "
            f"FROM linhas WHERE {condition}", tuple(args),
        ).fetchone()
        ranking = conn.execute(
            f"{base} SELECT fornecedor_id, fornecedor_nome, COUNT(DISTINCT pedido_id) AS pedidos, "
            "COALESCE(SUM(valor_pedido),0) AS valor_pedido, "
            "COALESCE(SUM(valor_recebido),0) AS valor_recebido, "
            "COALESCE(SUM(quantidade_pedida-quantidade_recebida),0) AS quantidade_pendente "
            f"FROM linhas WHERE {condition} GROUP BY fornecedor_id, fornecedor_nome "
            "ORDER BY valor_pedido DESC, fornecedor_nome ASC LIMIT 50", tuple(args),
        ).fetchall()
        rows = conn.execute(
            query_base + " ORDER BY data_pedido DESC, pedido_id DESC, pedido_item_id ASC LIMIT ? OFFSET ?",
            tuple([*args, limit, offset]),
        ).fetchall()
    itens = []
    for row in rows:
        item = dict(row)
        item["quantidade_pendente"] = round(float(item["quantidade_pedida"] or 0) - float(item["quantidade_recebida"] or 0), 3)
        for key in ("quantidade_pedida", "quantidade_recebida", "preco_unitario", "valor_pedido", "valor_recebido"):
            item[key] = _float(item.get(key))
        itens.append(item)
    return {
        "report_key": "compras.analitico", "kind": "analitico", "calculation_version": "1.0",
        "periodo": {"inicio": inicio, "fim": fim}, "filtros": dict(filters), "itens": itens,
        "resumo": {"pedidos": int(summary["pedidos"] or 0), "valor_pedido": _float(summary["valor_pedido"]),
                   "valor_recebido": _float(summary["valor_recebido"]), "quantidade_pendente": _float(summary["quantidade_pendente"])},
        "ranking_fornecedores": [
            {**dict(row), "pedidos": int(row["pedidos"] or 0),
             "valor_pedido": _float(row["valor_pedido"]),
             "valor_recebido": _float(row["valor_recebido"]),
             "quantidade_pendente": _float(row["quantidade_pendente"])}
            for row in ranking
        ],
        "paginacao": {"total": total, "limit": limit, "offset": offset, "proximo_offset": offset + limit if offset + limit < total else None},
    }


def estoque_analitico(filters: Mapping[str, object] | None = None) -> dict:
    filters = filters or {}
    limit, offset = _pagination(filters)
    deposito_id = _int_filter(filters, "deposito_id")
    where = ["p.ativo=1"]
    args: list[object] = []
    if deposito_id is not None:
        where.append("d.id=?")
        args.append(deposito_id)
    classe = str(filters.get("classe_abc") or "").strip().upper()
    if classe:
        if classe not in {"A", "B", "C"}:
            raise RelatorioOperacionalError("classe_abc deve ser A, B ou C")
        where.append("COALESCE(p.classe_abc,'C')=?")
        args.append(classe)
    termo = str(filters.get("q") or "").strip()
    if termo:
        like = f"%{termo}%"
        where.append("(p.nome ILIKE ? OR COALESCE(p.sku,'') ILIKE ?)")
        args.extend([like, like])
    situacao = str(filters.get("situacao") or "").strip().lower()
    if situacao not in {"", "normal", "ruptura", "reposicao", "excesso"}:
        raise RelatorioOperacionalError("situacao deve ser normal, ruptura, reposicao ou excesso")
    if situacao:
        situacao_sql = "CASE WHEN p.quantidade=0 THEN 'ruptura' WHEN p.estoque_maximo>0 AND p.quantidade>p.estoque_maximo THEN 'excesso' WHEN p.estoque_minimo>0 AND p.quantidade<=p.estoque_minimo THEN 'reposicao' ELSE 'normal' END"
        where.append(f"{situacao_sql}=?")
        args.append(situacao)
    base = """
        WITH posicao AS (
            SELECT p.id AS produto_id, p.ativo, p.sku, p.nome, p.classe_abc, p.classe_xyz,
                   d.id AS deposito_id, d.nome AS deposito_nome,
                   COALESCE(s.quantidade,0) AS quantidade, COALESCE(s.reserva,0) AS reserva,
                   COALESCE(s.bloqueado,0) AS bloqueado, COALESCE(s.separacao,0) AS separacao,
                   COALESCE(s.estoque_minimo,0) AS estoque_minimo, COALESCE(s.estoque_maximo,0) AS estoque_maximo,
                   COALESCE(s.custo_medio,p.custo_unitario,0) AS custo_medio
            FROM produtos_cadastro p CROSS JOIN depositos d
            LEFT JOIN estoque_saldo s ON s.produto_id=p.id AND s.deposito_id=d.id
        )
    """
    condition = " AND ".join(where)
    with system_conn() as conn:
        total = int(conn.execute(f"{base} SELECT COUNT(*) AS total FROM posicao p JOIN depositos d ON d.id=p.deposito_id WHERE {condition}", tuple(args)).fetchone()["total"] or 0)
        rows = conn.execute(
            f"{base} SELECT p.*, (p.quantidade-p.reserva-p.bloqueado-p.separacao) AS disponivel, "
            "(p.quantidade*p.custo_medio) AS valor, "
            "CASE WHEN p.quantidade=0 THEN 'ruptura' WHEN p.estoque_maximo>0 AND p.quantidade>p.estoque_maximo THEN 'excesso' "
            "WHEN p.estoque_minimo>0 AND p.quantidade<=p.estoque_minimo THEN 'reposicao' ELSE 'normal' END AS situacao "
            f"FROM posicao p JOIN depositos d ON d.id=p.deposito_id WHERE {condition} "
            "ORDER BY situacao ASC, valor DESC, p.nome ASC LIMIT ? OFFSET ?",
            tuple([*args, limit, offset]),
        ).fetchall()
    itens = []
    for row in rows:
        item = dict(row)
        for key in ("quantidade", "reserva", "bloqueado", "separacao", "estoque_minimo", "estoque_maximo", "custo_medio", "disponivel", "valor"):
            item[key] = _float(item.get(key))
        itens.append(item)
    return {
        "report_key": "estoque.analitico", "kind": "analitico", "calculation_version": "1.0",
        "filtros": dict(filters), "itens": itens,
        "paginacao": {"total": total, "limit": limit, "offset": offset, "proximo_offset": offset + limit if offset + limit < total else None},
    }


def necessidade_compra(filters: Mapping[str, object] | None = None) -> dict:
    """Expõe o motor de reposição como relatório paginado e exportável.

    O cálculo continua centralizado em ``motor_reposicao``; esta camada apenas
    aplica filtros de apresentação e garante que a origem da sugestão seja
    explícita para o comprador.
    """
    filters = filters or {}
    limit, offset = _pagination(filters)
    deposito_id = _int_filter(filters, "deposito_id")
    produto_id = _int_filter(filters, "produto_id")
    from catalog_server.services import motor_reposicao

    resultado = motor_reposicao.calcular(produto_id=produto_id, deposito_id=deposito_id)
    itens = resultado.get("sugestoes", [])
    classe = str(filters.get("classe_abc") or "").strip().upper()
    if classe:
        if classe not in {"A", "B", "C"}:
            raise RelatorioOperacionalError("classe_abc deve ser A, B ou C")
        itens = [item for item in itens if (item.get("classe_abc") or "C") == classe]
    termo = str(filters.get("q") or "").strip().lower()
    if termo:
        itens = [item for item in itens if termo in f"{item.get('nome') or ''} {item.get('sku') or ''}".lower()]
    somente = str(filters.get("somente_necessidade") or "").strip().lower()
    if somente in {"1", "true", "sim"}:
        itens = [item for item in itens if float(item.get("sugestao") or 0) > 0]
    elif somente not in {"", "0", "false", "nao", "não"}:
        raise RelatorioOperacionalError("somente_necessidade deve ser booleano")
    fornecedor_id = _int_filter(filters, "fornecedor_id")
    if fornecedor_id is not None:
        itens = [item for item in itens if item.get("fornecedor_id") == fornecedor_id]
    itens.sort(key=lambda item: (-float(item.get("sugestao") or 0), item.get("ruptura_provavel") or "9999", item.get("nome") or ""))
    total = len(itens)
    page = itens[offset:offset + limit]
    return {
        "report_key": "estoque.necessidade_compra", "kind": "analitico", "calculation_version": "1.0",
        "data": resultado.get("data"), "filtros": dict(filters), "itens": page,
        "resumo": {"produtos": total, "com_necessidade": sum(1 for item in itens if float(item.get("sugestao") or 0) > 0),
                   "total_sugerido": round(sum(float(item.get("sugestao") or 0) for item in itens), 3)},
        "paginacao": {"total": total, "limit": limit, "offset": offset, "proximo_offset": offset + limit if offset + limit < total else None},
    }
