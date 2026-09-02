from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, abort, render_template, send_from_directory, request

from catalog_server.config import PROJECT_DIR
from catalog_server.repositories import (
    catalog_repo,
    compras_repo,
    condicao_repo,
    emitente_repo,
    orcamento_repo,
    quote_repo,
)
from catalog_server.repositories.orcamentos import resumo_desconto
from catalog_server.services import quote_service
from catalog_server.blueprints.api_quotes import _enrich_itens
from catalog_server.repositories import loja
from catalog_server.services import boletos as boleto_service
from catalog_server.services import relatorios_clientes
from catalog_server.services import relatorios, exportacao_relatorios
from catalog_server import permissao
from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

pages_bp = Blueprint("pages", __name__)

# Build do frontend (Vite+TS); fonte única da SPA.
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

_ORC_STATUS_LABEL = {
    "rascunho": "Rascunho",
    "ativo": "Ativo",
    "em_analise": "Em análise",
    "liberado": "Liberado",
    "finalizado": "Finalizado",
    "recebido": "Recebido",
    "cancelado": "Cancelado",
    "devolvido": "Devolvido",
}


@pages_bp.get("/etiquetas/imprimir")
def etiquetas_imprimir():
    raw_ids = (request.args.get("ids") or "").split(",")
    if not request.args.get("ids") or any(not x.strip().isdigit() for x in raw_ids):
        abort(400, description="Informe ids de produtos válidos para imprimir etiquetas")
    ids = list(dict.fromkeys(int(x) for x in raw_ids))
    if any(pid <= 0 for pid in ids):
        abort(400, description="Informe ids de produtos válidos para imprimir etiquetas")
    etiquetas = loja.dados_etiquetas(ids)
    if not etiquetas:
        abort(404, description="Nenhum produto encontrado para impressão")
    return render_template("etiquetas.html", etiquetas=etiquetas)


@pages_bp.get("/orcamentos/<int:cotacao_id>/imprimir")
def quote_print(cotacao_id: int):
    data = quote_repo.get(cotacao_id)
    if data is None:
        abort(404)
    itens = _enrich_itens(data["itens"])
    doc = quote_service.document_context(
        data["cotacao"], itens, data["fornecedores"], data["vencedores"], data["precos"]
    )
    return render_template("quote_print.html", doc=doc)


@pages_bp.get("/compras/pedidos/<int:pedido_id>/imprimir")
def pedido_print(pedido_id: int):
    pedido = compras_repo.get_pedido(pedido_id)
    if pedido is None:
        abort(404)
    produtos = catalog_repo.products_by_ids([i["produto_id"] for i in pedido["itens"]])
    for i in pedido["itens"]:
        p = produtos.get(i["produto_id"], {})
        i["name"] = p.get("name", f"Produto #{i['produto_id']}")
        i["sku"] = p.get("sku", "")
        i["brand"] = p.get("brand", "")
        i["imagem_url"] = p.get("imagem_url")
    emitente = emitente_repo.get()
    return render_template("pedido_print.html", pedido=pedido, emitente=emitente)


@pages_bp.get("/orcamentos/venda/<int:orcamento_id>/imprimir")
def orcamento_venda_print(orcamento_id: int):
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        abort(404)
    emitente = emitente_repo.get()
    cond_nome = None
    if orc.get("condicao_pagamento_id"):
        cond = condicao_repo.get(orc["condicao_pagamento_id"])
        cond_nome = (cond or {}).get("nome")
    validade = None
    try:
        criado = datetime.strptime(str(orc["criado_em"])[:10], "%Y-%m-%d")
        validade = (criado + timedelta(days=int(orc.get("validade_dias") or 0))).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        pass
    return render_template(
        "orcamento_print.html",
        orc=orc,
        emitente=emitente,
        condicao_pagamento=cond_nome,
        validade=validade,
        status_label=_ORC_STATUS_LABEL.get(orc.get("status"), orc.get("status") or ""),
        desc_resumo=resumo_desconto(orc),
    )


@pages_bp.get("/orcamentos/<int:orcamento_id>/boleto")
def orcamento_boleto(orcamento_id: int):
    """Impressão do(s) boleto(s) das parcelas de uma venda a prazo."""
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        abort(404)
    emitente = emitente_repo.get()
    parcelas = boleto_service.parcelas_com_boleto(orc.get("numero") or "")
    cond_nome = None
    if orc.get("condicao_pagamento_id"):
        cond = condicao_repo.get(orc["condicao_pagamento_id"])
        cond_nome = (cond or {}).get("nome")
    return render_template(
        "boleto_print.html",
        orc=orc,
        emitente=emitente,
        parcelas=parcelas,
        condicao_pagamento=cond_nome,
    )


def _autorizar_pagina_relatorio(*, financeiro: bool = False) -> None:
    """Protege impressão HTML, que não passa pelo gate das rotas /api."""
    actor = usuario_id_requisicao()
    if not actor:
        abort(401, description="Sessão necessária para imprimir relatório")
    if not permissao.tem_permissao(actor, "relatorios", "visualizar"):
        abort(403, description="Permissão negada: relatorios.visualizar")
    if not permissao.tem_permissao(actor, "relatorios", "imprimir"):
        abort(403, description="Permissão negada: relatorios.imprimir")
    if financeiro and not permissao.tem_permissao(actor, "relatorios", "financeiro"):
        abort(403, description="Permissão negada: relatorios.financeiro")


@pages_bp.get("/relatorios/imprimir")
def relatorio_registrado_print():
    chave = (request.args.get("relatorio") or "").strip().lower()
    if chave not in {"dashboard", "vendas", "compras", "estoque", "financeiro", "financeiro.analitico", "vendas.analitico", "compras.analitico", "estoque.analitico", "estoque.necessidade_compra"}:
        abort(400, description="Relatório inválido")
    _autorizar_pagina_relatorio(financeiro=chave in {"financeiro", "financeiro.analitico"})
    try:
        data = relatorios.executar(chave, request.args.to_dict(flat=True))
        columns, rows = exportacao_relatorios.rows_for(chave, data)
    except (KeyError, ValueError, TypeError) as exc:
        abort(400, description=str(exc))
    titles = {"dashboard": "Resumo executivo", "vendas": "Vendas", "compras": "Compras", "estoque": "Estoque valorizado", "financeiro": "Financeiro / DRE", "financeiro.analitico": "Financeiro analítico", "vendas.analitico": "Vendas analíticas", "compras.analitico": "Compras analíticas", "estoque.analitico": "Posição de estoque", "estoque.necessidade_compra": "Necessidade de compra"}
    return render_template(
        "relatorio_generico_print.html",
        titulo=titles[chave],
        chave=chave,
        data=data,
        columns=columns,
        rows=rows,
        orientacao="portrait" if chave == "dashboard" else "landscape",
        gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


@pages_bp.get("/relatorios/clientes/imprimir")
def relatorio_clientes_print():
    _autorizar_pagina_relatorio()
    try:
        data = relatorios_clientes.clientes(request.args.to_dict(flat=True))
    except relatorios_clientes.RelatorioFiltroError as exc:
        abort(400, description=str(exc))
    return render_template(
        "relatorio_clientes_print.html",
        data=data,
        modo="clientes",
        gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


@pages_bp.get("/relatorios/clientes/<int:cliente_id>/compras/imprimir")
def relatorio_compras_cliente_print(cliente_id: int):
    _autorizar_pagina_relatorio()
    try:
        data = relatorios_clientes.compras_cliente(cliente_id, request.args.to_dict(flat=True))
    except LookupError:
        abort(404)
    except relatorios_clientes.RelatorioFiltroError as exc:
        abort(400, description=str(exc))
    return render_template(
        "relatorio_clientes_print.html",
        data=data,
        modo="compras",
        gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
