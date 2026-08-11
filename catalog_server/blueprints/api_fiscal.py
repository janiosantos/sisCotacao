from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import cfop_repo, cst_repo, fiscal_config_repo

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
    fiscal_config_repo.upsert(
        variante_id,
        ncm=data.get("ncm"),
        cfop=data.get("cfop"),
        cst_icms=data.get("cst_icms"),
        cst_pis=data.get("cst_pis"),
        cst_cofins=data.get("cst_cofins"),
        aliquota_icms=float(data.get("aliquota_icms") or 0),
        aliquota_pis=float(data.get("aliquota_pis") or 0),
        aliquota_cofins=float(data.get("aliquota_cofins") or 0),
        aliquota_ipi=float(data.get("aliquota_ipi") or 0),
    )
    return jsonify({"ok": True})


@api_fiscal_bp.post("/api/fiscal/config/gerar")
def gerar_config():
    data = request.get_json(silent=True) or {}
    cfop = data.get("cfop", "5.102")
    cst = data.get("cst_icms", "00")
    count = fiscal_config_repo.gerar_config_padrao(cfop_padrao=cfop, cst_icms=cst)
    return jsonify({"gerados": count})
