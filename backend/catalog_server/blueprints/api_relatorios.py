"""API de relatórios e indicadores + endpoints legados.

Os endpoints novos de clientes usam um contrato analítico separado para não
alterar silenciosamente consumidores antigos da central de BI.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from catalog_server import permissao
from catalog_server.repositories.relatorios import relatorio_repo
from catalog_server.services import relatorios
from catalog_server.services import relatorios_clientes
from catalog_server.services import exportacao_relatorios
from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

api_relatorios_bp = Blueprint("api_relatorios", __name__)


# ─── Endpoints legados (v2.x) ──────────────────────────────

@api_relatorios_bp.get("/api/relatorios/vendas-periodo")
def vendas_periodo():
    ini = request.args.get("inicio", "")
    fim = request.args.get("fim", "")
    return jsonify(relatorio_repo.vendas_por_periodo(ini, fim))


@api_relatorios_bp.get("/api/relatorios/aging-receber")
def aging_receber():
    return jsonify(relatorio_repo.aging_receber())


@api_relatorios_bp.get("/api/relatorios/aging-pagar")
def aging_pagar():
    return jsonify(relatorio_repo.aging_pagar())


@api_relatorios_bp.get("/api/relatorios/dre")
def dre():
    ini = request.args.get("inicio", "")
    fim = request.args.get("fim", "")
    return jsonify(relatorio_repo.dre_resumido(ini, fim))


@api_relatorios_bp.get("/api/relatorios/margem-vendas")
def margem_vendas():
    ini = request.args.get("inicio", "")
    fim = request.args.get("fim", "")
    return jsonify(relatorio_repo.margem_vendas(ini, fim))


# ─── BI-001..007 ───────────────────────────────────────────


@api_relatorios_bp.get("/api/relatorios/central")
def central():
    return jsonify(relatorios.central())


@api_relatorios_bp.get("/api/relatorios/dashboard")
def dashboard():
    return jsonify(relatorios.dashboard_executivo(request.args.get("data_inicio"), request.args.get("data_fim")))


@api_relatorios_bp.get("/api/relatorios/vendas")
def vendas():
    return jsonify(relatorios.vendas(
        request.args.get("data_inicio"), request.args.get("data_fim"),
        request.args.get("agrupamento") or "produto",
    ))


@api_relatorios_bp.get("/api/relatorios/compras")
def compras():
    return jsonify(relatorios.compras(request.args.get("data_inicio"), request.args.get("data_fim")))


@api_relatorios_bp.get("/api/relatorios/estoque")
def estoque():
    return jsonify(relatorios.estoque(request.args.get("deposito_id", type=int)))


@api_relatorios_bp.get("/api/relatorios/financeiro")
def financeiro():
    actor = usuario_id_requisicao()
    if not actor or not permissao.tem_permissao(actor, "relatorios", "financeiro"):
        return jsonify({"error": "Permissão negada: relatorios.financeiro", "code": "permissao_negada"}), 403
    return jsonify(relatorios.financeiro(request.args.get("data_inicio"), request.args.get("data_fim")))


@api_relatorios_bp.get("/api/relatorios/exportar")
def exportar_relatorio_registrado():
    """Exporta relatórios existentes; o cliente escolhe apenas uma chave registrada."""
    actor = _actor_for("exportar")
    if not actor:
        return jsonify({"error": "Permissão negada: relatorios.exportar", "code": "permissao_negada"}), 403
    chave = (request.args.get("relatorio") or "").strip().lower()
    formato = (request.args.get("formato") or "csv").lower()
    if chave not in {"dashboard", "vendas", "compras", "estoque", "financeiro"}:
        return jsonify({"error": "relatorio inválido", "code": "relatorio_invalido"}), 400
    if chave == "financeiro" and not permissao.tem_permissao(actor, "relatorios", "financeiro"):
        return jsonify({"error": "Permissão negada: relatorios.financeiro", "code": "permissao_negada"}), 403
    if formato not in {"csv", "xlsx"}:
        return jsonify({"error": "formato deve ser csv ou xlsx", "code": "formato_invalido"}), 400
    filtros = _filters()
    try:
        data = relatorios.executar(chave, filtros)
        content = (exportacao_relatorios.csv_bytes if formato == "csv" else exportacao_relatorios.xlsx_bytes)(
            chave, data, actor_id=actor, filtros=filtros, ip=request.remote_addr
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "filtro_relatorio_invalido"}), 400
    ext = "csv" if formato == "csv" else "xlsx"
    mimetype = "text/csv" if ext == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return send_file(BytesIO(content), mimetype=mimetype, as_attachment=True, download_name=f"relatorio-{chave}.{ext}")


# ─── Relatórios analíticos de clientes ─────────────────────

def _actor_for(action: str = "visualizar") -> int:
    actor = usuario_id_requisicao()
    if not actor or not permissao.tem_permissao(actor, "relatorios", action):
        return 0
    return int(actor)


def _filters() -> dict[str, object]:
    return request.args.to_dict(flat=True)


@api_relatorios_bp.get("/api/relatorios/clientes")
def relatorio_clientes():
    try:
        return jsonify(relatorios_clientes.clientes(_filters()))
    except relatorios_clientes.RelatorioFiltroError as exc:
        return jsonify({"error": str(exc), "code": "filtro_relatorio_invalido"}), 400


@api_relatorios_bp.get("/api/relatorios/clientes/aniversariantes")
def relatorio_aniversariantes():
    filtros = _filters()
    filtros.setdefault("sort", "data_nascimento")
    if not filtros.get("aniversario_inicio") and not filtros.get("aniversario_fim"):
        hoje = date.today()
        filtros["aniversario_inicio"] = hoje.isoformat()
        filtros["aniversario_fim"] = hoje.isoformat()
    else:
        filtros.setdefault("aniversario_inicio", filtros.get("data_inicio"))
        filtros.setdefault("aniversario_fim", filtros.get("data_fim"))
    try:
        return jsonify(relatorios_clientes.clientes(filtros))
    except relatorios_clientes.RelatorioFiltroError as exc:
        return jsonify({"error": str(exc), "code": "filtro_relatorio_invalido"}), 400


@api_relatorios_bp.get("/api/relatorios/clientes/compras")
def relatorio_compras_cliente():
    cliente_id = request.args.get("cliente_id", type=int)
    if not cliente_id:
        return jsonify({"error": "cliente_id é obrigatório", "code": "cliente_obrigatorio"}), 400
    try:
        return jsonify(relatorios_clientes.compras_cliente(cliente_id, _filters()))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cliente_nao_encontrado"}), 404
    except relatorios_clientes.RelatorioFiltroError as exc:
        return jsonify({"error": str(exc), "code": "filtro_relatorio_invalido"}), 400


@api_relatorios_bp.get("/api/relatorios/clientes/exportar")
def exportar_clientes():
    actor = _actor_for("exportar")
    if not actor:
        return jsonify({"error": "Permissão negada: relatorios.exportar", "code": "permissao_negada"}), 403
    formato = (request.args.get("formato") or "csv").lower()
    filtros = _filters()
    try:
        data = relatorios_clientes.clientes(filtros)
        if formato == "csv":
            content = exportacao_relatorios.csv_bytes("clientes", data, actor_id=actor, filtros=filtros, ip=request.remote_addr)
            return send_file(BytesIO(content), mimetype="text/csv", as_attachment=True, download_name="clientes.csv")
        if formato == "xlsx":
            content = exportacao_relatorios.xlsx_bytes("clientes", data, actor_id=actor, filtros=filtros, ip=request.remote_addr)
            return send_file(BytesIO(content), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="clientes.xlsx")
        return jsonify({"error": "formato deve ser csv ou xlsx", "code": "formato_invalido"}), 400
    except relatorios_clientes.RelatorioFiltroError as exc:
        return jsonify({"error": str(exc), "code": "filtro_relatorio_invalido"}), 400


@api_relatorios_bp.get("/api/relatorios/clientes/compras/exportar")
def exportar_compras_cliente():
    actor = _actor_for("exportar")
    if not actor:
        return jsonify({"error": "Permissão negada: relatorios.exportar", "code": "permissao_negada"}), 403
    cliente_id = request.args.get("cliente_id", type=int)
    if not cliente_id:
        return jsonify({"error": "cliente_id é obrigatório", "code": "cliente_obrigatorio"}), 400
    formato = (request.args.get("formato") or "csv").lower()
    filtros = _filters()
    try:
        data = relatorios_clientes.compras_cliente(cliente_id, filtros)
        if formato == "csv":
            content = exportacao_relatorios.csv_bytes("clientes.compras", data, actor_id=actor, filtros=filtros, ip=request.remote_addr)
            name = f"cliente-{cliente_id}-compras.csv"
            return send_file(BytesIO(content), mimetype="text/csv", as_attachment=True, download_name=name)
        if formato == "xlsx":
            content = exportacao_relatorios.xlsx_bytes("clientes.compras", data, actor_id=actor, filtros=filtros, ip=request.remote_addr)
            name = f"cliente-{cliente_id}-compras.xlsx"
            return send_file(BytesIO(content), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=name)
        return jsonify({"error": "formato deve ser csv ou xlsx", "code": "formato_invalido"}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cliente_nao_encontrado"}), 404
    except relatorios_clientes.RelatorioFiltroError as exc:
        return jsonify({"error": str(exc), "code": "filtro_relatorio_invalido"}), 400
