from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import plano_conta_repo
from catalog_server.services import classificacao_financeira
from catalog_server.blueprints.api_usuarios import usuario_id_requisicao

api_plano_contas_bp = Blueprint("api_plano_contas", __name__)


def _flag(value: object) -> bool:
    return value is True or value == 1 or str(value).lower() in ("1", "true", "on", "sim")


@api_plano_contas_bp.get("/api/plano-contas")
def listar():
    tipo = request.args.get("tipo") or None
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    natureza = request.args.get("natureza") or None
    rateavel_raw = request.args.get("rateavel")
    rateavel = None if rateavel_raw in (None, "") else rateavel_raw.lower() in ("1", "true", "on", "sim")
    if natureza and natureza not in classificacao_financeira.NATUREZAS:
        return jsonify({"error": "Natureza de custo inválida", "code": "filtro_invalido"}), 400
    return jsonify(plano_conta_repo.list(
        tipo=tipo, somente_ativos=somente_ativos, natureza=natureza, rateavel=rateavel
    ))


@api_plano_contas_bp.get("/api/plano-contas/<int:conta_id>")
def detalhar(conta_id: int):
    conta = plano_conta_repo.get(conta_id)
    if not conta:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify(conta)


@api_plano_contas_bp.get("/api/plano-contas/<int:conta_id>/uso")
def uso(conta_id: int):
    result = plano_conta_repo.uso(conta_id)
    if not result:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify(result)


@api_plano_contas_bp.post("/api/plano-contas")
def criar():
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    tipo = data.get("tipo") or "receita"
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome da conta"}), 400
    if tipo not in ("receita", "despesa"):
        return jsonify({"error": "Tipo deve ser receita ou despesa"}), 400
    natureza = data.get("natureza_custo") or ("fora_precificacao" if tipo == "receita" else None)
    politica = data.get("politica_rateio") or ("nao_incluir" if tipo == "receita" else None)
    if tipo == "despesa" and (not natureza or not politica):
        return jsonify({"error": "Informe natureza e política de rateio da despesa", "code": "classificacao_obrigatoria"}), 400
    try:
        if natureza not in classificacao_financeira.NATUREZAS or politica not in classificacao_financeira.POLITICAS:
            raise ValueError("Natureza ou política de rateio inválida")
        if natureza in {"nao_rateavel", "fora_precificacao"} and politica != "nao_incluir":
            raise ValueError("Natureza não rateável deve usar política não incluir")
        conta_id = plano_conta_repo.create(
            codigo, nome, tipo, data.get("pai_id") or None, natureza, politica,
            _flag(data.get("exige_centro_custo")), _flag(data.get("exige_competencia")),
            _flag(data.get("permite_rateio")), data.get("componente_variavel"), usuario_id_requisicao(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "classificacao_invalida"}), 400
    return jsonify({"id": conta_id}), 201


@api_plano_contas_bp.put("/api/plano-contas/<int:conta_id>")
def atualizar(conta_id: int):
    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    nome = (data.get("nome") or "").strip()
    tipo = data.get("tipo") or "receita"
    if not codigo or not nome:
        return jsonify({"error": "Informe código e nome da conta"}), 400
    if tipo not in ("receita", "despesa"):
        return jsonify({"error": "Tipo deve ser receita ou despesa"}), 400
    natureza = data.get("natureza_custo") or ("fora_precificacao" if tipo == "receita" else None)
    politica = data.get("politica_rateio") or ("nao_incluir" if tipo == "receita" else None)
    if tipo == "despesa" and (not natureza or not politica):
        return jsonify({"error": "Informe natureza e política de rateio da despesa", "code": "classificacao_obrigatoria"}), 400
    try:
        if natureza not in classificacao_financeira.NATUREZAS or politica not in classificacao_financeira.POLITICAS:
            raise ValueError("Natureza ou política de rateio inválida")
        if natureza in {"nao_rateavel", "fora_precificacao"} and politica != "nao_incluir":
            raise ValueError("Natureza não rateável deve usar política não incluir")
        ok = plano_conta_repo.update(
            conta_id, codigo, nome, tipo, data.get("pai_id") or None, natureza, politica,
            _flag(data.get("exige_centro_custo")), _flag(data.get("exige_competencia")),
            _flag(data.get("permite_rateio")), data.get("componente_variavel"), usuario_id_requisicao(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "classificacao_invalida"}), 400
    if not ok:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify({"ok": True})


@api_plano_contas_bp.patch("/api/plano-contas/<int:conta_id>/ativo")
def alternar_ativo(conta_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    ok = plano_conta_repo.set_ativo(conta_id, ativo)
    if not ok:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify({"ok": True})
