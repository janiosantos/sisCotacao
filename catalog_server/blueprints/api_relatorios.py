from flask import Blueprint, jsonify, request
from catalog_server.repositories.relatorios import relatorio_repo

api_relatorios_bp = Blueprint("api_relatorios", __name__)


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
