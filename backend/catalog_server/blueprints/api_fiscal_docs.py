"""API de emissão de documentos fiscais (NFC-e/NF-e) via Tecnospeed."""
from __future__ import annotations

import hmac
import os

from flask import Blueprint, jsonify, request

from catalog_server.repositories.fiscal_documentos import (
    documento_fiscal_repo,
    tecnospeed_config_repo,
)
from catalog_server.services import tecnospeed
from catalog_server.fiscal.snapshot import (
    montar_contextos_orcamento,
    persistir as persistir_snapshot,
)


def _capturar_snapshot(orcamento_id: int, tipo_doc: str) -> None:
    """Best-effort: registra o snapshot fiscal do orçamento emitido.
    Falha de snapshot NUNCA impede a emissão."""
    try:
        for ctx_dados, result in montar_contextos_orcamento(orcamento_id):
            vid = ctx_dados.get('product_id') if isinstance(ctx_dados, dict) else getattr(ctx_dados, 'product_id', None)
            data_op = ctx_dados.get('operation_date', '') if isinstance(ctx_dados, dict) else getattr(ctx_dados, 'operation_date', '')
            persistir_snapshot(
                documento_tipo=tipo_doc,
                documento_id=orcamento_id,
                variante_id=vid,
                operation_date=data_op or None,
                result=result,
            )
    except Exception:
        pass

api_fiscal_docs_bp = Blueprint("api_fiscal_docs", __name__)


@api_fiscal_docs_bp.post("/api/orcamentos/<int:orcamento_id>/nfce")
def emitir_nfce(orcamento_id: int):
    try:
        doc = tecnospeed.emitir_nfce(orcamento_id)
    except tecnospeed.TecnospeedError as e:
        return jsonify({"error": str(e)}), 400
    _capturar_snapshot(orcamento_id, "65")
    return jsonify(doc), 201


@api_fiscal_docs_bp.get("/api/orcamentos/<int:orcamento_id>/nfce")
def status_nfce(orcamento_id: int):
    doc = documento_fiscal_repo.get_by_orcamento(orcamento_id, "65")
    if doc is None:
        return jsonify({"status": "nao_emitido"}), 200
    if doc["status"] == "processando":
        try:
            doc = tecnospeed.consultar_status(doc["id"])
        except tecnospeed.TecnospeedError:
            pass  # mantém o último status conhecido; o polling do front tenta de novo
    return jsonify(doc)


@api_fiscal_docs_bp.post("/api/orcamentos/<int:orcamento_id>/nfe")
def emitir_nfe(orcamento_id: int):
    """NF-e (modelo 55) — venda B2B faturada. Exige que o orçamento tenha
    um cliente vinculado (cliente_id) com CNPJ/CPF, IE e endereço
    completos cadastrados."""
    try:
        doc = tecnospeed.emitir_nfe(orcamento_id)
    except tecnospeed.TecnospeedError as e:
        return jsonify({"error": str(e)}), 400
    _capturar_snapshot(orcamento_id, "55")
    return jsonify(doc), 201


@api_fiscal_docs_bp.get("/api/orcamentos/<int:orcamento_id>/nfe")
def status_nfe(orcamento_id: int):
    doc = documento_fiscal_repo.get_by_orcamento(orcamento_id, "55")
    if doc is None:
        return jsonify({"status": "nao_emitido"}), 200
    if doc["status"] == "processando":
        try:
            doc = tecnospeed.consultar_status(doc["id"])
        except tecnospeed.TecnospeedError:
            pass
    return jsonify(doc)


@api_fiscal_docs_bp.get("/api/tecnospeed/config")
def get_config():
    cfg = tecnospeed_config_repo.get_all()
    cfg["token"] = "••••••••" if cfg.get("token") else ""  # nunca devolve o token em texto puro
    return jsonify(cfg)


@api_fiscal_docs_bp.put("/api/tecnospeed/config")
def set_config():
    data = request.get_json(silent=True) or {}
    permitido = {"ambiente", "simulado", "token", "cnpj_emitente", "serie_nfce", "serie_nfe"}
    chaves = {k: v for k, v in data.items() if k in permitido}
    if "token" in chaves and chaves["token"] == "••••••••":
        del chaves["token"]  # front reenviou o placeholder mascarado; não sobrescreve
    if "ambiente" in chaves and chaves["ambiente"] not in ("homologacao", "producao"):
        return jsonify({"error": "Ambiente inválido"}), 400
    cfg = tecnospeed_config_repo.set(chaves)
    cfg["token"] = "••••••••" if cfg.get("token") else ""
    return jsonify(cfg)


@api_fiscal_docs_bp.post("/api/webhooks/tecnospeed")
def webhook_tecnospeed():
    """Endpoint público que a Tecnospeed chama quando o status de uma nota
    emitida assincronamente muda (autorizada/rejeitada pela SEFAZ)."""
    expected = os.getenv("TECNOSPEED_WEBHOOK_SECRET", "")
    received = request.headers.get("X-Webhook-Secret", "")
    if expected:
        if not hmac.compare_digest(received, expected):
            return jsonify({"error": "Webhook não autorizado"}), 401
    elif os.getenv("CATALOG_ENV", "development").lower() == "production":
        return jsonify({"error": "Webhook não configurado"}), 503

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not payload:
        return jsonify({"error": "Payload de webhook inválido"}), 400
    tecnospeed.processar_webhook(payload)
    return jsonify({"ok": True})


# ─── Provedor alternativo: Focus NFe ───────────────────────

@api_fiscal_docs_bp.post("/api/orcamentos/<int:orcamento_id>/focus/<modelo>")
def emitir_focus(orcamento_id: int, modelo: str):
    """Emite NFC-e/NF-e via Focus NFe (provedor alternativo ao TecnoSpeed)."""
    from catalog_server.services import focus_emissao

    if modelo not in ("55", "65"):
        return jsonify({"error": "modelo inválido (55 ou 65)"}), 400
    try:
        doc = focus_emissao.emitir(orcamento_id, modelo)
    except focus_emissao.FocusEmissaoError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(doc), 201


@api_fiscal_docs_bp.get("/api/orcamentos/<int:orcamento_id>/focus/<modelo>")
def consultar_focus(orcamento_id: int, modelo: str):
    from catalog_server.services import focus_emissao

    try:
        return jsonify(focus_emissao.consultar(orcamento_id, modelo))
    except focus_emissao.FocusEmissaoError as e:
        return jsonify({"error": str(e)}), 400
