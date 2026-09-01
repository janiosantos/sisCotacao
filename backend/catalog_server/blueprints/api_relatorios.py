"""API de relatórios e indicadores (BI-001..007) + endpoints legados."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories.relatorios import relatorio_repo
from catalog_server.services import relatorios

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
    return jsonify(relatorios.financeiro(request.args.get("data_inicio"), request.args.get("data_fim")))