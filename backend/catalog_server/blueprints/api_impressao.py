"""API da retaguarda de impressão (PDV).

- POST /api/impressao/orcamentos/<id>   enfileira o cupom do orçamento.
- POST /api/impressao/teste             envia cupom de teste para a porta.
- GET  /api/impressao/config            lê destino/auto da impressora.
- PUT  /api/impressao/config            atualiza destino/auto.
- GET  /api/impressao/fila              status da fila (jobs recentes).
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

from catalog_server.repositories.orcamentos import orcamento_repo
from catalog_server.services.impressao import impressao_service
from catalog_server import permissao

api_impressao_bp = Blueprint("api_impressao", __name__)


@api_impressao_bp.get("/api/impressao/config")
def get_config():
    return jsonify(impressao_service.config())


@api_impressao_bp.put("/api/impressao/config")
@permissao.exige_permissao("impressao", "configurar")
def put_config():
    data = request.get_json(silent=True) or {}
    impressao_service.salvar_config(data)
    return jsonify(impressao_service.config())


@api_impressao_bp.post("/api/impressao/orcamentos/<int:orcamento_id>")
@permissao.exige_permissao("impressao", "imprimir")
def imprimir_orcamento(orcamento_id: int):
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    job_id = impressao_service.enfileirar(orc)
    return jsonify({"ok": True, "job_id": job_id, "numero": orc.get("numero")}), 202


@api_impressao_bp.post("/api/impressao/teste")
@permissao.exige_permissao("impressao", "imprimir")
def imprimir_teste():
    orc = {
        "numero": "TESTE",
        "cliente": "Cupom de teste",
        "contato": "",
        "criado_em": "",
        "subtotal": 12.5,
        "desconto": 0.0,
        "total": 12.5,
        "observacoes": "Enviado pela retaguarda do PDV.",
        "itens": [
            {"nome": "Produto Exemplo", "quantidade": 1, "preco_unitario": 12.5, "subtotal": 12.5},
        ],
    }
    job_id = impressao_service.enfileirar(orc)
    return jsonify({"ok": True, "job_id": job_id}), 202


@api_impressao_bp.get("/api/impressao/fila")
def fila():
    return jsonify(impressao_service.status())


@api_impressao_bp.post("/api/impressao/fila/<int:job_id>/reimprimir")
@permissao.exige_permissao("impressao", "imprimir")
def reimprimir(job_id: int):
    try:
        novo_id = impressao_service.reenfileirar(job_id, usuario_id_requisicao())
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "job_nao_encontrado"}), 404
    return jsonify({"ok": True, "novo_job_id": novo_id}), 202