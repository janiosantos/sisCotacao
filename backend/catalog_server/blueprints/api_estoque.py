from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.db import system_conn
from catalog_server.repositories import deposito_repo, estoque_repo, expedicao_repo, lote_repo

api_estoque_bp = Blueprint("api_estoque", __name__)


# ─── Depósitos ─────────────────────────────────────────────

@api_estoque_bp.get("/api/depositos")
def listar_depositos():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    return jsonify(deposito_repo.list(somente_ativos=somente_ativos))


@api_estoque_bp.get("/api/depositos/<int:deposito_id>")
def detalhar_deposito(deposito_id: int):
    d = deposito_repo.get(deposito_id)
    if not d:
        return jsonify({"error": "Depósito não encontrado"}), 404
    return jsonify(d)


@api_estoque_bp.post("/api/depositos")
def criar_deposito():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do depósito"}), 400
    deposito_id = deposito_repo.create(nome)
    return jsonify({"id": deposito_id}), 201


@api_estoque_bp.put("/api/depositos/<int:deposito_id>")
def atualizar_deposito(deposito_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome do depósito"}), 400
    if not deposito_repo.update(deposito_id, nome):
        return jsonify({"error": "Depósito não encontrado"}), 404
    return jsonify({"ok": True})


@api_estoque_bp.patch("/api/depositos/<int:deposito_id>/ativo")
def alternar_ativo_deposito(deposito_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    if not deposito_repo.set_ativo(deposito_id, ativo):
        return jsonify({"error": "Depósito não encontrado"}), 404
    return jsonify({"ok": True})


# ─── Saldo ─────────────────────────────────────────────────

@api_estoque_bp.get("/api/estoque/saldo")
def consultar_saldo():
    deposito_id = request.args.get("deposito_id", type=int)
    variante_id = request.args.get("variante_id", type=int)
    familia_id = request.args.get("familia_id", type=int)
    q = request.args.get("q", "").strip()
    termo = q if q else None
    return jsonify(estoque_repo.saldo(
        deposito_id=deposito_id, variante_id=variante_id, termo=termo, familia_id=familia_id
    ))


# ─── Movimento ─────────────────────────────────────────────

@api_estoque_bp.post("/api/estoque/movimento")
def registrar_movimento():
    data = request.get_json(silent=True) or {}
    deposito_id = data.get("deposito_id")
    variante_id = data.get("variante_id")
    tipo = (data.get("tipo") or "").strip()
    quantidade = float(data.get("quantidade") or 0)

    erros = []
    if not deposito_id:
        erros.append("deposito_id")
    if not variante_id:
        erros.append("variante_id")
    if tipo not in ("entrada", "saida", "ajuste", "transferencia", "inventario"):
        erros.append("tipo inválido")
    if quantidade <= 0:
        erros.append("quantidade deve ser positiva")
    if erros:
        return jsonify({"error": "Campos inválidos: " + ", ".join(erros)}), 400

    # Valida se a variante existe
    with system_conn() as conn:
        if not conn.execute("SELECT 1 FROM variantes WHERE id=?", (variante_id,)).fetchone():
            return jsonify({"error": f"Variante {variante_id} não encontrada"}), 404
        if not conn.execute("SELECT 1 FROM depositos WHERE id=?", (deposito_id,)).fetchone():
            return jsonify({"error": f"Depósito {deposito_id} não encontrado"}), 404

    result = estoque_repo.movimentar(
        deposito_id=deposito_id,
        variante_id=variante_id,
        tipo=tipo,
        quantidade=quantidade,
        documento=data.get("documento"),
        observacao=data.get("observacao"),
        lote_id=data.get("lote_id"),
        usuario_id=data.get("usuario_id"),
    )
    return jsonify(result), 201


@api_estoque_bp.get("/api/estoque/movimento")
def listar_movimentos():
    deposito_id = request.args.get("deposito_id", type=int)
    variante_id = request.args.get("variante_id", type=int)
    tipo = request.args.get("tipo") or None
    limit = request.args.get("limit", 100, type=int)
    return jsonify(estoque_repo.movimentos(deposito_id=deposito_id, variante_id=variante_id, tipo=tipo, limit=limit))


# ─── Transferência ─────────────────────────────────────────

@api_estoque_bp.post("/api/estoque/transferir")
def transferir():
    data = request.get_json(silent=True) or {}
    erros = []
    origem_id = data.get("origem_id")
    destino_id = data.get("destino_id")
    variante_id = data.get("variante_id")
    quantidade = float(data.get("quantidade") or 0)
    if not origem_id:
        erros.append("origem_id")
    if not destino_id:
        erros.append("destino_id")
    if not variante_id:
        erros.append("variante_id")
    if quantidade <= 0:
        erros.append("quantidade deve ser positiva")
    if erros:
        return jsonify({"error": "Campos inválidos: " + ", ".join(erros)}), 400
    result = estoque_repo.transferir(
        origem_id, destino_id, variante_id, quantidade, data.get("observacao"), data.get("usuario_id")
    )
    return jsonify(result), 201


# ─── Lotes ─────────────────────────────────────────────────

@api_estoque_bp.get("/api/estoque/lotes")
def listar_lotes():
    deposito_id = request.args.get("deposito_id", type=int)
    variante_id = request.args.get("variante_id", type=int)
    return jsonify(lote_repo.list(deposito_id=deposito_id, variante_id=variante_id))


@api_estoque_bp.get("/api/estoque/lotes/<int:lote_id>")
def detalhar_lote(lote_id: int):
    l = lote_repo.get(lote_id)
    if not l:
        return jsonify({"error": "Lote não encontrado"}), 404
    return jsonify(l)


@api_estoque_bp.patch("/api/estoque/saldo/<int:saldo_id>/limites")
def atualizar_limites(saldo_id: int):
    data = request.get_json(silent=True) or {}
    with system_conn() as conn:
        conn.execute(
            "UPDATE estoque_saldo SET estoque_minimo=?, estoque_maximo=? WHERE id=?",
            (float(data.get("estoque_minimo", 0)), float(data.get("estoque_maximo", 0)), saldo_id),
        )
    return jsonify({"ok": True})


@api_estoque_bp.post("/api/estoque/lotes")
def criar_lote():
    data = request.get_json(silent=True) or {}
    erros = []
    deposito_id = data.get("deposito_id")
    variante_id = data.get("variante_id")
    codigo = (data.get("codigo") or "").strip()
    if not deposito_id:
        erros.append("deposito_id")
    if not variante_id:
        erros.append("variante_id")
    if not codigo:
        erros.append("codigo")
    if erros:
        return jsonify({"error": "Campos inválidos: " + ", ".join(erros)}), 400
    lote_id = lote_repo.create(
        deposito_id, variante_id, codigo,
        quantidade=float(data.get("quantidade") or 0),
        data_fabricacao=data.get("data_fabricacao"),
        data_validade=data.get("data_validade"),
    )
    return jsonify({"id": lote_id}), 201


# ─── Expedição ─────────────────────────────────────────────

@api_estoque_bp.get("/api/expedicao")
def listar_expedicao():
    return jsonify(expedicao_repo.list(
        deposito_id=request.args.get("deposito_id", type=int),
        status=request.args.get("status"),
    ))


@api_estoque_bp.post("/api/expedicao")
def criar_expedicao():
    data = request.get_json(silent=True) or {}
    dep_id = data.get("deposito_id")
    codigo = (data.get("codigo") or "").strip()
    if not dep_id or not codigo:
        return jsonify({"error": "deposito_id e codigo obrigatórios"}), 400
    exp_id = expedicao_repo.create(codigo, dep_id, data.get("transportadora", ""), data.get("observacao", ""))
    return jsonify({"id": exp_id}), 201


@api_estoque_bp.post("/api/expedicao/<int:exp_id>/status")
def atualizar_status_expedicao(exp_id: int):
    data = request.get_json(silent=True) or {}
    if not expedicao_repo.update_status(exp_id, data.get("status", "")):
        return jsonify({"error": "Expedição não encontrada"}), 404
    return jsonify({"ok": True})


# ─── Fatos auditáveis (ADR 0003) ───────────────────────────

@api_estoque_bp.post('/api/estoque/movimentos')
def criar_movimento_fato():
    dados = request.get_json(silent=True) or {}
    try:
        r = estoque_repo.movimentar_fato(
            int(dados['deposito_id']), int(dados['variante_id']),
            dados.get('tipo', 'entrada'), float(dados.get('quantidade') or 0),
            idempotency_key=dados.get('idempotency_key'),
            origem_tipo=dados.get('origem_tipo', ''),
            origem_id=dados.get('origem_id'),
            documento=dados.get('documento'), observacao=dados.get('observacao'),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(r), 200 if r.get('duplicado') else 201


@api_estoque_bp.post('/api/estoque/reservas')
def reservar_estoque():
    dados = request.get_json(silent=True) or {}
    try:
        r = estoque_repo.movimentar_fato(
            int(dados['deposito_id']), int(dados['variante_id']),
            'reserva', float(dados.get('quantidade') or 0),
            idempotency_key=dados.get('idempotency_key'),
            origem_tipo=dados.get('origem_tipo', 'orcamento'),
            origem_id=dados.get('origem_id'),
            observacao=dados.get('observacao'),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(r), 200 if r.get('duplicado') else 201


@api_estoque_bp.post('/api/estoque/reservas/liberar')
def liberar_reserva():
    dados = request.get_json(silent=True) or {}
    try:
        r = estoque_repo.movimentar_fato(
            int(dados['deposito_id']), int(dados['variante_id']),
            'liberacao', float(dados.get('quantidade') or 0),
            idempotency_key=dados.get('idempotency_key'),
            origem_tipo=dados.get('origem_tipo', ''),
            origem_id=dados.get('origem_id'),
            observacao=dados.get('observacao'),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(r), 200


@api_estoque_bp.get('/api/estoque/reconciliacao')
def reconciliar_estoque_api():
    deposito_id = int(request.args.get('deposito_id', 0))
    variante_id = int(request.args.get('variante_id', 0))
    if not deposito_id or not variante_id:
        return jsonify({'error': 'informe deposito_id e variante_id'}), 400
    return jsonify(estoque_repo.reconciliar(deposito_id, variante_id))


@api_estoque_bp.get('/api/estoque/reconciliacao/tudo')
def reconciliar_tudo_api():
    dep = request.args.get('deposito_id', type=int)
    return jsonify({'divergencias': estoque_repo.reconciliar_tudo(dep)})


@api_estoque_bp.post('/api/estoque/inventarios')
def lancar_inventario_api():
    dados = request.get_json(silent=True) or {}
    try:
        r = estoque_repo.lancar_inventario(
            int(dados['deposito_id']), int(dados['variante_id']),
            float(dados.get('quantidade_contada') or 0),
            justificativa=dados.get('justificativa', ''),
            idempotency_key=dados.get('idempotency_key'),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(r), 200 if r.get('duplicado') else 201
