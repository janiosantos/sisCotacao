"""API de infraestrutura: idempotência (ARC-003), reconciliação (ARC-005),
auditoria (ARC-006), conciliação bancária (INT-001) e comunicação (INT-006)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
from catalog_server.services import conciliacao, infra, reconciliacao, comunicacao, operacao

api_infra_bp = Blueprint("api_infra", __name__)


# ─── Reconciliação (ARC-005) ───────────────────────────────

@api_infra_bp.get("/api/infra/reconciliacao")
def reconciliacao_divergencias():
    return jsonify(reconciliacao.divergencias())


# ─── Auditoria (ARC-006) ───────────────────────────────────

@api_infra_bp.get("/api/infra/auditoria")
def auditoria():
    return jsonify({"eventos": infra.listar(
        request.args.get("alvo_tipo"), request.args.get("alvo_id"), int(request.args.get("limite") or 200),
    )})


# ─── Conciliação bancária (INT-001) ────────────────────────

@api_infra_bp.post("/api/infra/contas-bancarias")
def criar_conta_bancaria():
    data = request.get_json(silent=True) or {}
    if not data.get("banco"):
        return jsonify({"error": "banco é obrigatório", "code": "conta_invalida"}), 400
    return jsonify({"id": conciliacao.criar_conta(data["banco"], data.get("agencia"), data.get("conta"))}), 201


@api_infra_bp.post("/api/infra/contas-bancarias/<int:conta_id>/extrato")
def importar_extrato(conta_id: int):
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(conciliacao.importar_extrato(conta_id, data.get("movimentos") or []))
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "extrato_invalido"}), 400


@api_infra_bp.post("/api/infra/contas-bancarias/<int:conta_id>/sugerir")
def sugerir_matching(conta_id: int):
    return jsonify({"sugestoes": conciliacao.sugerir_matching(conta_id, float(request.args.get("tolerancia") or 0.01))})


@api_infra_bp.post("/api/infra/movimentos-bancarios/<int:movimento_id>/aprovar")
def aprovar_conciliacao(movimento_id: int):
    try:
        return jsonify(conciliacao.aprovar(movimento_id, usuario_id_requisicao()))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "movimento_nao_encontrado"}), 404


@api_infra_bp.post("/api/infra/movimentos-bancarios/<int:movimento_id>/rejeitar")
def rejeitar_conciliacao(movimento_id: int):
    try:
        return jsonify(conciliacao.rejeitar(movimento_id, usuario_id_requisicao()))
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "movimento_nao_encontrado"}), 404


@api_infra_bp.get("/api/infra/contas-bancarias/<int:conta_id>/movimentos")
def listar_movimentos(conta_id: int):
    return jsonify({"movimentos": conciliacao.listar(conta_id, request.args.get("status"))})


# ─── Comunicação (INT-006) ─────────────────────────────────

@api_infra_bp.get("/api/infra/comunicacao")
def listar_comunicacao():
    return jsonify({"envios": comunicacao.listar_envios(
        request.args.get("status"), int(request.args.get("limite") or 50),
    )})


# ─── Cobrança/adquirentes (INT-002) ────────────────────────

@api_infra_bp.get("/api/infra/cobrancas/pendentes")
def cobrancas_pendentes():
    return jsonify(operacao.reconciliar_pendentes(int(request.args.get("limite") or 100)))


# ─── Carga inicial (ADM-001) ───────────────────────────────

@api_infra_bp.post("/api/infra/carga")
def importar_carga():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(operacao.importar_carga(data.get("tipo") or "", data.get("itens") or []))
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "carga_invalida"}), 400


# ─── Deduplicação (ADM-002) ────────────────────────────────

@api_infra_bp.get("/api/infra/deduplicacao/candidatos")
def candidatos_duplicidade():
    return jsonify({"candidatos": operacao.candidatos(request.args.get("tipo") or "sku")})


@api_infra_bp.post("/api/infra/deduplicacao/merge")
def merge_duplicados():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(operacao.merge(int(data["primario"]), int(data["duplicado"]), data.get("tipo") or "produto"))
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "merge_invalido"}), 400