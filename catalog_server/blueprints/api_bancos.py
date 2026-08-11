from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories import banco_repo

api_bancos_bp = Blueprint("api_bancos", __name__)


# ─── Contas Bancárias ──────────────────────────────────────

@api_bancos_bp.get("/api/bancos/contas")
def listar_contas():
    somente_ativas = request.args.get("somente_ativos", "").lower() in ("1", "true")
    return jsonify(banco_repo.listar_contas(somente_ativas=somente_ativas))


@api_bancos_bp.get("/api/bancos/contas/<int:conta_id>")
def detalhar_conta(conta_id: int):
    c = banco_repo.get_conta(conta_id)
    if not c:
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify(c)


@api_bancos_bp.post("/api/bancos/contas")
def criar_conta():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da conta"}), 400
    conta_id = banco_repo.criar_conta(
        nome, data.get("banco", "000"),
        data.get("agencia", ""), data.get("conta", ""),
        data.get("digito", ""), float(data.get("saldo_inicial") or 0),
    )
    return jsonify({"id": conta_id}), 201


@api_bancos_bp.put("/api/bancos/contas/<int:conta_id>")
def atualizar_conta(conta_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome"}), 400
    if not banco_repo.atualizar_conta(
        conta_id, nome, data.get("banco", "000"),
        data.get("agencia", ""), data.get("conta", ""), data.get("digito", ""),
    ):
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify({"ok": True})


@api_bancos_bp.patch("/api/bancos/contas/<int:conta_id>/ativo")
def alternar_ativo(conta_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    if not banco_repo.set_ativo(conta_id, ativo):
        return jsonify({"error": "Conta não encontrada"}), 404
    return jsonify({"ok": True})


# ─── Movimento ─────────────────────────────────────────────

@api_bancos_bp.get("/api/bancos/movimentos")
def listar_movimentos():
    conta_id = request.args.get("conta_id", type=int)
    limit = request.args.get("limit", 200, type=int)
    return jsonify(banco_repo.listar_movimentos(conta_id=conta_id, limit=limit))


@api_bancos_bp.post("/api/bancos/movimentos")
def criar_movimento():
    data = request.get_json(silent=True) or {}
    conta_id = data.get("conta_id")
    tipo = (data.get("tipo") or "").strip()
    valor = float(data.get("valor") or 0)
    data_mov = data.get("data_movimento")
    if not conta_id or tipo not in ("credito", "debito", "transferencia") or valor <= 0 or not data_mov:
        return jsonify({"error": "conta_id, tipo, valor e data_movimento obrigatórios"}), 400
    result = banco_repo.criar_movimento(
        conta_id, tipo, valor, data_mov,
        descricao=data.get("descricao", ""),
        documento=data.get("documento", ""),
        categoria=data.get("categoria", ""),
        plano_conta_id=data.get("plano_conta_id"),
    )
    return jsonify(result), 201


@api_bancos_bp.post("/api/bancos/movimentos/<int:mov_id>/conciliar")
def toggle_conciliar(mov_id: int):
    if not banco_repo.toggle_conciliado(mov_id):
        return jsonify({"error": "Movimento não encontrado"}), 404
    return jsonify({"ok": True})
