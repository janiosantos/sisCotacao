"""API dos gatilhos contábeis configuráveis por evento (v2.15.0)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server import contabil_gatilhos
from catalog_server.repositories import plano_conta_repo

api_contabil_bp = Blueprint("api_contabil", __name__)


@api_contabil_bp.get("/api/contabil/gatilhos")
def listar_gatilhos():
    return jsonify({
        "gatilhos": contabil_gatilhos.listar_gatilhos(),
        "eventos": contabil_gatilhos.EVENTOS_SUPORTADOS,
    })


@api_contabil_bp.put("/api/contabil/gatilhos/<evento_tipo>")
def configurar_gatilho(evento_tipo: str):
    if evento_tipo not in contabil_gatilhos.EVENTOS_SUPORTADOS:
        return jsonify({"error": f"evento_tipo inválido: {evento_tipo}"}), 400
    dados = request.get_json(silent=True) or {}
    debito = dados.get("debito_conta_id")
    credito = dados.get("credito_conta_id")
    ativo = bool(dados.get("ativo", False))
    try:
        gatilho = contabil_gatilhos.configurar(
            evento_tipo,
            debito_conta_id=int(debito) if debito else None,
            credito_conta_id=int(credito) if credito else None,
            ativo=ativo,
            descricao=dados.get("descricao") or "",
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(gatilho)


@api_contabil_bp.get("/api/contabil/lancamentos")
def listar_lancamentos():
    limite = request.args.get("limite", 100, type=int)
    return jsonify({"lancamentos": contabil_gatilhos.listar_lancamentos(limite)})