import csv, io

from flask import Blueprint, jsonify, request
from catalog_server.repositories import emitente_repo, ibpt_repo, nfe_entrada_repo, nfe_saida_repo

api_fiscal_avancado_bp = Blueprint("api_fiscal_avancado", __name__)


@api_fiscal_avancado_bp.get("/api/emitente")
def get_emitente():
    e = emitente_repo.get()
    return jsonify(e or {})


@api_fiscal_avancado_bp.put("/api/emitente")
def upsert_emitente():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": emitente_repo.upsert(data)})


@api_fiscal_avancado_bp.get("/api/nfe-saida")
def listar_nfe_saida():
    return jsonify(nfe_saida_repo.list(status=request.args.get("status")))


@api_fiscal_avancado_bp.get("/api/nfe-entrada")
def listar_nfe_entrada():
    return jsonify(nfe_entrada_repo.list())


@api_fiscal_avancado_bp.get("/api/ibpt")
def listar_ibpt():
    return jsonify(ibpt_repo.list(ncm=request.args.get("ncm"), limit=request.args.get("limit", 100, type=int)))


@api_fiscal_avancado_bp.post("/api/ibpt")
def upsert_ibpt():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": ibpt_repo.upsert(
        data["ncm"], data.get("descricao", ""),
        float(data.get("aliquota_federal", 0)),
        float(data.get("aliquota_estadual", 0)),
        float(data.get("aliquota_municipal", 0)),
    )}), 201
