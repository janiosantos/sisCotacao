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

from flask import Blueprint, current_app, jsonify, request

from catalog_server.db import system_conn
from catalog_server.payments import service as payment_service
from catalog_server.payments.base import WebhookNaoAutorizado
from catalog_server.payments.registry import ProviderIndisponivel
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
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Falha inesperada ao emitir cobrança")
        return jsonify({"error": "Não foi possível emitir a cobrança"}), 502
    return jsonify(resultado)


@api_payments_bp.get("/api/financeiro/receber/<int:conta_id>/cobranca/status")
def consultar_cobranca(conta_id: int):
    try:
        return jsonify(payment_service.consultar(conta_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Falha inesperada ao consultar cobrança")
        return jsonify({"error": "Não foi possível consultar a cobrança"}), 502


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

    ext = os.path.splitext(arquivo.filename)[1].lower() or ".png"
    if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
        return jsonify({"error": "Formato de comprovante não permitido"}), 400
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
    if not isinstance(payload, dict) or not payload:
        return jsonify({"error": "Payload de webhook inválido"}), 400
    try:
        resultado = payment_service.processar_webhook(
            provider, payload, dict(request.headers), request.args.to_dict()
        )
    except WebhookNaoAutorizado as exc:
        return jsonify({"error": str(exc)}), 401
    except ProviderIndisponivel as exc:
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Falha inesperada ao processar webhook de pagamento")
        return jsonify({"error": "Webhook não processado"}), 502
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
    if data.get("operacao") not in ("boleto", "pix"):
        return jsonify({"error": "operacao deve ser boleto ou pix"}), 400
    if data.get("ambiente") not in ("sandbox", "producao"):
        return jsonify({"error": "ambiente deve ser sandbox ou producao"}), 400
    for field in ("client_id", "client_secret", "access_token", "api_key", "certificado", "conta", "chave_pix", "webhook_secret"):
        if field in data and not isinstance(data[field], str):
            return jsonify({"error": f"{field} deve ser texto"}), 400
    payment_provider_repo.upsert_config(data)
    return jsonify({"ok": True})
