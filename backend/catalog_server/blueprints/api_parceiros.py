from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
from catalog_server.services import parceiros

api_parceiros_bp = Blueprint("api_parceiros", __name__)


@api_parceiros_bp.get("/api/parceiros")
def listar_parceiros():
    return jsonify({"parceiros": parceiros.listar(
        request.args.get("status"), request.args.get("categoria"), request.args.get("q"),
    )})


@api_parceiros_bp.post("/api/parceiros")
def criar_parceiro():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(parceiros.criar(
            int(data["cliente_id"]), data.get("categoria"), usuario_id_requisicao(), data.get("observacao"),
        )), 201
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "parceiro_invalido"}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "cliente_nao_encontrado"}), 404


@api_parceiros_bp.patch("/api/parceiros/<int:parceiro_id>/status")
def alterar_status(parceiro_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(parceiros.alterar_status(parceiro_id, data.get("status"), usuario_id_requisicao()))
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "status_parceiro_invalido"}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "parceiro_nao_encontrado"}), 404


@api_parceiros_bp.post("/api/parceiros/<int:parceiro_id>/indicacoes")
def criar_indicacao(parceiro_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(parceiros.criar_indicacao(parceiro_id, data.get("cliente_id"))), 201
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "parceiro_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "indicacao_invalida"}), 400


@api_parceiros_bp.post("/api/parceiros/indicacoes/<int:indicacao_id>/converter")
def converter_indicacao(indicacao_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(parceiros.converter_indicacao(
            indicacao_id, int(data["orcamento_id"]), usuario_id_requisicao(),
        ))
    except (KeyError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "conversao_indicacao_invalida"}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "indicacao_nao_encontrada"}), 404


@api_parceiros_bp.post("/api/parceiros/bonus/<int:bonus_id>/aprovar")
def aprovar_bonus(bonus_id: int):
    try:
        return jsonify(parceiros.aprovar_bonus(bonus_id, usuario_id_requisicao()))
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "bonus_invalido"}), 400


@api_parceiros_bp.post("/api/parceiros/bonus/<int:bonus_id>/pagar")
def pagar_bonus(bonus_id: int):
    try:
        return jsonify(parceiros.pagar_bonus(bonus_id, usuario_id_requisicao()))
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "bonus_invalido"}), 400


@api_parceiros_bp.get("/api/parceiros/<int:parceiro_id>/ledger")
def ledger_parceiro(parceiro_id: int):
    try:
        return jsonify(parceiros.ledger(parceiro_id))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "parceiro_nao_encontrado"}), 404
