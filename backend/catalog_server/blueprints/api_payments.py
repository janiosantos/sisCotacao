"""API de pagamentos (boleto/PIX) das contas a receber (v2.23.0).

- POST /api/financeiro/receber/<id>/cobranca   → emite boleto ou PIX
- GET  /api/financeiro/receber/<id>/cobranca/status → consulta status
- POST /api/financeiro/receber/<id>/comprovante → anexa comprovante (depósito/TED)
- POST /api/webhooks/payments/<provider>        → webhook (baixa automática)
- GET/PUT /api/payment-providers                → configuração (Integrações)
- GET/PUT /api/payment-providers/config         → credenciais por provider/operação
"""
from __future__ import annotations

import os
import uuid

from flask import Blueprint, jsonify, request

from catalog_server.db import system_conn
from catalog_server.payments import service as payment_service
from catalog_server.payments.repo import payment_provider_repo

api_payments_bp = Blueprint("api_payments", __name__)


def _ambiente() -> str:
    return request.args.get("ambiente", "sandbox")


# ─── Emissão de cobrança (boleto/PIX) ──────────────────────

@api_payments_bp.post("/api/financeiro/receber/<int:conta_id>/cobranca")
def emitir_cobranca(conta_id: int):
    data = request.get_json(silent=True) or {}
    operacao = (data.get("operacao") or "boleto").strip().lower()
    if operacao not in ("boleto", "pix"):
        return jsonify({"error": "operacao deve ser boleto ou pix"}), 400
    try:
        resultado = payment_service.emitir(conta_id, operacao, _ambiente())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(resultado)


@api_payments_bp.get("/api/financeiro/receber/<int:conta_id>/cobranca/status")
def consultar_cobranca(conta_id: int):
    try:
        return jsonify(payment_service.consultar(conta_id))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ─── Comprovante (depósito/TED) ─────────────────────────────

@api_payments_bp.post("/api/financeiro/receber/<int:conta_id>/comprovante")
def anexar_comprovante(conta_id: int):
    from catalog_server.blueprints.api_usuarios import SESSION_KEY
    from flask import session

    tipo = (request.form.get("tipo") or "deposito").strip()
    descricao = (request.form.get("descricao") or "").strip()
    arquivo = request.files.get("file")
    if not arquivo or not arquivo.filename:
        return jsonify({"error": "Informe o comprovante (arquivo)"}), 400

    ext = os.path.splitext(arquivo.filename)[1] or ".png"
    filename = f"comprovante_{conta_id}_{uuid.uuid4().hex[:12]}{ext}"
    # salva em diretório dedicado de comprovantes
    base = os.environ.get("COMPROVANTES_DIR", "/app/images/comprovantes")
    os.makedirs(base, exist_ok=True)
    arquivo.save(os.path.join(base, filename))

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO conta_comprovante (conta_id, tipo, filename, descricao, usuario_id)"
            " VALUES (?,?,?,?,?)",
            (conta_id, tipo, filename, descricao, session.get(SESSION_KEY)),
        )
        conn.commit()
    return jsonify({"ok": True, "filename": filename})


# ─── Webhook (baixa automática) ─────────────────────────────

@api_payments_bp.post("/api/webhooks/payments/<provider>")
def webhook_payment(provider: str):
    payload = request.get_json(silent=True) or {}
    try:
        resultado = payment_service.processar_webhook(provider, payload, dict(request.headers))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(resultado)


# ─── Configuração (Integrações de pagamento) ────────────────

@api_payments_bp.get("/api/payment-providers")
def listar_providers():
    return jsonify({
        "providers": payment_provider_repo.list_providers(),
        "configs": payment_provider_repo.list_configs(),
    })


@api_payments_bp.put("/api/payment-providers/config")
def upsert_config():
    data = request.get_json(silent=True) or {}
    if not data.get("provider_id"):
        return jsonify({"error": "provider_id obrigatório"}), 400
    payment_provider_repo.upsert_config(data)
    return jsonify({"ok": True})