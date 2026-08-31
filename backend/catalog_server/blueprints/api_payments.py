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
from catalog_server.services import webhook_log

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
    from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

    tipo = (request.form.get("tipo") or "deposito").strip()
    descricao = (request.form.get("descricao") or "").strip()
    arquivo = request.files.get("file")
    if not arquivo or not arquivo.filename:
        return jsonify({"error": "Informe o comprovante (arquivo)"}), 400

    ext = os.path.splitext(arquivo.filename)[1].lower() or ".png"
    if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
        return jsonify({"error": "Formato de comprovante não permitido"}), 400
    assinatura = arquivo.stream.read(16)
    arquivo.stream.seek(0)
    assinaturas = {
        ".pdf": assinatura.startswith(b"%PDF-"),
        ".png": assinatura.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": assinatura.startswith(b"\xff\xd8\xff"),
        ".jpeg": assinatura.startswith(b"\xff\xd8\xff"),
    }
    if not assinaturas[ext]:
        return jsonify({"error": "O conteúdo não corresponde ao formato informado"}), 400
    filename = f"comprovante_{conta_id}_{uuid.uuid4().hex[:12]}{ext}"
    # salva em diretório dedicado de comprovantes
    base = os.environ.get("COMPROVANTES_DIR", "/app/images/comprovantes")
    os.makedirs(base, exist_ok=True)
    caminho = os.path.join(base, filename)
    try:
        arquivo.save(caminho)
        with system_conn() as conn:
            conn.execute(
                "INSERT INTO conta_comprovante (conta_id, tipo, filename, descricao, usuario_id)"
                " VALUES (?,?,?,?,?)",
                (conta_id, tipo, filename, descricao, usuario_id_requisicao()),
            )
            conn.commit()
    except Exception:
        # Não deixa arquivo órfão se a persistência do registro falhar.
        try:
            os.remove(caminho)
        except OSError:
            pass
        current_app.logger.exception("Falha ao salvar comprovante")
        return jsonify({"error": "Não foi possível salvar o comprovante"}), 500
    return jsonify({"ok": True, "filename": filename})


# ─── Webhook (baixa automática) ─────────────────────────────

def _evento_do_payload(provider: str, payload: dict) -> tuple[str | None, str | None]:
    """Extrai (evento, payment_id) do payload de forma genérica por provedor."""
    if provider == "asaas":
        pay = payload.get("payment") or {}
        return payload.get("event"), str(pay.get("id") or "")
    if provider == "mercadopago":
        data = payload.get("data") or {}
        return payload.get("type"), str(data.get("id") or "")
    if provider == "efipay":
        pix = payload.get("pix") or {}
        charge = payload.get("charge") or {}
        return payload.get("type"), str(pix.get("txid") or charge.get("id") or "")
    if provider == "sicoob":
        pixs = payload.get("pix") or []
        return "pix", str((pixs[0] or {}).get("txid") or "") if pixs else None
    return None, str((payload.get("payment") or {}).get("id") or "")


def _status_do_resultado(r: dict) -> str:
    if r.get("duplicado"):
        return "duplicado"
    if r.get("ignorado"):
        return "ignorado"
    if r.get("caixa_pendente"):
        return "caixa_pendente"
    return "processado"


@api_payments_bp.post("/api/webhooks/payments/<provider>")
def webhook_payment(provider: str):
    ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not payload:
        webhook_log.registrar(provider, "payload_invalido", http_status=400, ip=ip,
                              payload=payload)
        return jsonify({"error": "Payload de webhook inválido"}), 400
    evento, payment_id = _evento_do_payload(provider, payload)
    try:
        resultado = payment_service.processar_webhook(
            provider, payload, dict(request.headers), request.args.to_dict()
        )
        status = _status_do_resultado(resultado)
        webhook_log.registrar(provider, status, http_status=200, assinatura_ok=True,
                              ip=ip, payload=payload, evento=evento, payment_id=payment_id)
        return jsonify(resultado)
    except WebhookNaoAutorizado as exc:
        webhook_log.registrar(provider, "nao_autorizado", http_status=401, ip=ip,
                              payload=payload, erro=str(exc), evento=evento, payment_id=payment_id)
        return jsonify({"error": str(exc)}), 401
    except ProviderIndisponivel as exc:
        webhook_log.registrar(provider, "nao_configurado", http_status=503, ip=ip,
                              payload=payload, erro=str(exc), evento=evento, payment_id=payment_id)
        # enfileira rechecagem da conta no outbox — quando o provedor for configurado,
        # o worker baixa a conta automaticamente (sem depender de nova notificação).
        if payment_id:
            from catalog_server.services import outbox

            outbox.enfileirar(
                "webhook.rechecagem",
                {"payment_id": payment_id, "provider": provider},
                chave_idempotencia=f"webhook:{provider}:{payment_id}",
            )
        return jsonify({"error": str(exc)}), 503
    except ValueError as exc:
        webhook_log.registrar(provider, "erro", http_status=400, ip=ip,
                              payload=payload, erro=str(exc), evento=evento, payment_id=payment_id)
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Falha inesperada ao processar webhook de pagamento")
        webhook_log.registrar(provider, "erro", http_status=502, ip=ip,
                              payload=payload, erro="exceção inesperada", evento=evento,
                              payment_id=payment_id)
        return jsonify({"error": "Webhook não processado"}), 502


# ─── Logs de webhook e rechecagem ───────────────────────────

@api_payments_bp.get("/api/webhooks/logs")
def listar_webhook_logs():
    rows, total = webhook_log.listar(
        provider=(request.args.get("provider") or "").strip(),
        status=(request.args.get("status") or "").strip(),
        desde=(request.args.get("desde") or "").strip(),
        limite=min(200, max(1, request.args.get("limit", 50, type=int))),
        offset=max(0, request.args.get("offset", 0, type=int)),
    )
    return jsonify({"items": rows, "total": total})


@api_payments_bp.get("/api/webhooks/logs/<int:log_id>")
def detalhe_webhook_log(log_id: int):
    log = webhook_log.detalhe(log_id)
    if not log:
        return jsonify({"error": "Log não encontrado"}), 404
    return jsonify(log)


@api_payments_bp.post("/api/webhooks/rechecagem")
def rechecagem_webhooks():
    data = request.get_json(silent=True) or {}
    try:
        resultado = webhook_log.rechecagem(
            provider=(data.get("provider") or "").strip(),
            limite=max(1, min(200, int(data.get("limite") or 50))),
        )
    except Exception as exc:
        current_app.logger.exception("Falha na rechecagem de webhooks")
        return jsonify({"error": "Rechecagem falhou"}), 500
    return jsonify(resultado)


# ─── Outbox (operações assíncronas) ─────────────────────────

@api_payments_bp.get("/api/webhooks/outbox")
def listar_outbox():
    from catalog_server.services import outbox

    rows = outbox.listar(status=(request.args.get("status") or "").strip(),
                         limite=min(200, max(1, request.args.get("limit", 50, type=int))))
    return jsonify({"items": rows, "pendentes": outbox.pendentes_contagem()})


@api_payments_bp.post("/api/webhooks/outbox/rodar")
def rodar_outbox():
    from catalog_server.services import outbox
    from catalog_server.jobs import tasks

    try:
        resultado = tasks.rodar_outbox(limite=50)
        return jsonify(resultado)
    except Exception as exc:
        current_app.logger.exception("Falha ao processar outbox")
        return jsonify({"error": f"Outbox falhou: {exc}"}), 400


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
