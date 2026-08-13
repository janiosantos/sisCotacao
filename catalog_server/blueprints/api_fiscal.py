from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from catalog_server.blueprints.api_usuarios import SESSION_KEY
from catalog_server.repositories import (
    beneficio_fiscal_repo,
    cest_repo,
    cfop_repo,
    csosn_repo,
    cst_repo,
    fiscal_config_repo,
)
from catalog_server.services.fiscal_engine import calculate as fiscal_calcular
from catalog_server.services import fiscal_motor

api_fiscal_bp = Blueprint("api_fiscal", __name__)


# ─── CFOP ──────────────────────────────────────────────────

@api_fiscal_bp.get("/api/fiscal/cfop")
def listar_cfop():
    tipo = request.args.get("tipo") or None
    return jsonify(cfop_repo.list(tipo=tipo))


# ─── CST ───────────────────────────────────────────────────

@api_fiscal_bp.get("/api/fiscal/cst/<tabela>")
def listar_cst(tabela: str):
    if tabela not in ("cst_icms", "cst_pis", "cst_cofins"):
        return jsonify({"error": "tabela inválida"}), 400
    return jsonify(cst_repo.list(tabela))


# ─── CEST / CSOSN / Benefícios ─────────────────────────────

@api_fiscal_bp.get("/api/fiscal/cest")
def listar_cest():
    ncm = request.args.get("ncm") or None
    return jsonify(cest_repo.list(ncm=ncm))


@api_fiscal_bp.get("/api/fiscal/csosn")
def listar_csosn():
    return jsonify(csosn_repo.list())


@api_fiscal_bp.get("/api/fiscal/beneficios")
def listar_beneficios():
    return jsonify(beneficio_fiscal_repo.list(somente_ativos=True))


# ─── Config Fiscal ─────────────────────────────────────────

@api_fiscal_bp.get("/api/fiscal/config")
def listar_config():
    page = request.args.get("page", 0, type=int)
    limit = request.args.get("limit", 100, type=int)
    q = request.args.get("q", "").strip() or None
    return jsonify(fiscal_config_repo.list(page=page, limit=limit, termo=q))


@api_fiscal_bp.get("/api/fiscal/config/<int:variante_id>")
def get_config(variante_id: int):
    cfg = fiscal_config_repo.get(variante_id)
    if not cfg:
        return jsonify({"error": "Config não encontrada"}), 404
    return jsonify(cfg)


@api_fiscal_bp.put("/api/fiscal/config/<int:variante_id>")
def upsert_config(variante_id: int):
    data = request.get_json(silent=True) or {}
    num = lambda k: float(data[k]) if k in data and data[k] is not None else None
    tipo = "atualizado" if fiscal_config_repo.get(variante_id) else "criado"
    fiscal_config_repo.upsert(
        variante_id,
        ncm=data.get("ncm"),
        cfop=data.get("cfop"),
        cst_icms=data.get("cst_icms"),
        cst_pis=data.get("cst_pis"),
        cst_cofins=data.get("cst_cofins"),
        aliquota_icms=num("aliquota_icms"),
        aliquota_pis=num("aliquota_pis"),
        aliquota_cofins=num("aliquota_cofins"),
        aliquota_ipi=num("aliquota_ipi"),
        origem=int(data["origem"]) if data.get("origem") is not None else None,
        cest=data.get("cest"),
        csosn=data.get("csosn"),
        aliquota_icms_st=num("aliquota_icms_st"),
        mva=num("mva"),
        base_reducao=num("base_reducao"),
        aliquota_interestadual=num("aliquota_interestadual"),
        aliquota_fecp=num("aliquota_fecp"),
        credito_icms=num("credito_icms"),
        beneficio_id=int(data["beneficio_id"]) if data.get("beneficio_id") else None,
        vigencia_inicio=data.get("vigencia_inicio"),
        vigencia_fim=data.get("vigencia_fim"),
    )
    fiscal_config_repo.registrar_historico_config(variante_id, tipo, session.get(SESSION_KEY))
    return jsonify({"ok": True})


@api_fiscal_bp.post("/api/fiscal/config/gerar")
def gerar_config():
    data = request.get_json(silent=True) or {}
    cfop = data.get("cfop", "5.102")
    cst = data.get("cst_icms", "00")
    count = fiscal_config_repo.gerar_config_padrao(cfop_padrao=cfop, cst_icms=cst)
    return jsonify({"gerados": count})


# ─── Motor Fiscal (cálculo) ────────────────────────────────

@api_fiscal_bp.get("/api/fiscal/calcular/<int:variante_id>")
def calcular(variante_id: int):
    operacao = request.args.get("operacao", "compra")
    uf_dest = request.args.get("uf_dest") or None
    resultado = fiscal_calcular(variante_id, operacao=operacao, uf_dest=uf_dest)
    if resultado is None:
        return jsonify({"error": "Config fiscal não encontrada para esta variante"}), 404
    return jsonify(resultado)


@api_fiscal_bp.get("/api/fiscal/historico")
def listar_historico_fiscal():
    return jsonify(fiscal_config_repo.list_historico(
        termo=request.args.get("q"),
        variante_id=request.args.get("variante_id", type=int),
        limit=request.args.get("limit", 200, type=int),
    ))


# ─── Motor fiscal (contexto → resultado) ───────────────────

@api_fiscal_bp.post("/api/fiscal/simular")
def simular_operacao():
    """Simula uma operação: produto + cliente/UF + operação + data → FiscalResult + validação."""
    dados = request.get_json(silent=True) or {}
    resultado = fiscal_motor.simular(dados)
    return jsonify({
        "resultado": resultado,
        "status_validacao": resultado["status_validacao"],
        "problemas": resultado["problemas"],
    })
