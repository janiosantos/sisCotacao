from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.db import system_conn
from catalog_server.repositories import deposito_repo, estoque_repo, expedicao_repo, lote_repo
from catalog_server.repositories import loja as loja_repo
from catalog_server.services import estoque_parametro as parametro_svc
from catalog_server.services import inventario_ciclo as inventario_svc
from catalog_server.services import endereco as endereco_svc
from catalog_server.services import lote_rastreabilidade
from catalog_server.services import abc_historica
from catalog_server.services import xyz as xyz_svc
from catalog_server.services import demanda as demanda_svc
from catalog_server.blueprints.api_usuarios import usuario_id_requisicao
from catalog_server import contabil_gatilhos

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
    produto_id = request.args.get("produto_id", type=int)
    familia_id = request.args.get("familia_id", type=int)
    q = request.args.get("q", "").strip()
    termo = q if q else None
    return jsonify(estoque_repo.saldo(
        deposito_id=deposito_id, produto_id=produto_id, termo=termo,
        familia_id=familia_id,
    ))


@api_estoque_bp.get("/api/estoque/disponibilidade/<int:produto_id>")
def consultar_disponibilidade(produto_id: int):
    """Fórmula única de disponibilidade (EST-001): físico − reservado − bloqueado − separação, por depósito."""
    deposito_id = request.args.get("deposito_id", type=int)
    return jsonify({"produto_id": produto_id, "depositos": loja_repo.disponibilidade(produto_id, deposito_id)})


@api_estoque_bp.get("/api/estoque/valorizacao")
def consultar_valorizacao():
    """Valorização do estoque por depósito (quantidade × custo médio), opcionalmente por data de corte (EST-004)."""
    deposito_id = request.args.get("deposito_id", type=int)
    if not deposito_id:
        return jsonify({"error": "deposito_id é obrigatório", "code": "deposito_obrigatorio"}), 400
    data_corte = request.args.get("data_corte") or None
    produto_id = request.args.get("produto_id", type=int)
    return jsonify(estoque_repo.valorizar(deposito_id, data_corte=data_corte, produto_id=produto_id))


# ─── Parâmetros de planejamento (EST-005) ──────────────────


@api_estoque_bp.get("/api/estoque/parametros")
def listar_parametros():
    produto_id = request.args.get("produto_id", type=int)
    deposito_id = request.args.get("deposito_id", type=int)
    if not produto_id:
        return jsonify({"error": "produto_id é obrigatório", "code": "produto_obrigatorio"}), 400
    return jsonify({"parametros": parametro_svc.listar(produto_id, deposito_id)})


@api_estoque_bp.get("/api/estoque/parametros/efetivo")
def parametro_efetivo():
    produto_id = request.args.get("produto_id", type=int)
    deposito_id = request.args.get("deposito_id", type=int)
    if not produto_id or not deposito_id:
        return jsonify({"error": "produto_id e deposito_id são obrigatórios", "code": "parametro_obrigatorio"}), 400
    return jsonify(parametro_svc.obter_efetivo(produto_id, deposito_id))


@api_estoque_bp.post("/api/estoque/parametros")
def salvar_parametro():
    data = request.get_json(silent=True) or {}
    try:
        p = parametro_svc.salvar(
            int(data["produto_id"]),
            int(data["deposito_id"]),
            data.get("politica") or "manual",
            float(data["minimo"]) if data.get("minimo") is not None else None,
            float(data["maximo"]) if data.get("maximo") is not None else None,
            float(data["ponto_pedido"]) if data.get("ponto_pedido") is not None else None,
            float(data["estoque_seguranca"]) if data.get("estoque_seguranca") is not None else None,
            int(data["lead_time_dias"]) if data.get("lead_time_dias") else None,
            float(data["lote_minimo"]) if data.get("lote_minimo") is not None else None,
            float(data["lote_maximo"]) if data.get("lote_maximo") is not None else None,
            float(data["lote_multiplo"]) if data.get("lote_multiplo") is not None else None,
            data.get("calendario"),
            data.get("fonte_valor") or "manual",
            data.get("motivo"),
            usuario_id_requisicao(),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "parametro_invalido"}), 400
    return jsonify({"parametro": p})


@api_estoque_bp.delete("/api/estoque/parametros")
def excluir_parametro():
    produto_id = request.args.get("produto_id", type=int)
    deposito_id = request.args.get("deposito_id", type=int)
    if not produto_id or not deposito_id:
        return jsonify({"error": "produto_id e deposito_id são obrigatórios", "code": "parametro_obrigatorio"}), 400
    if not parametro_svc.excluir(produto_id, deposito_id):
        return jsonify({"error": "Parâmetro não encontrado", "code": "parametro_nao_encontrado"}), 404
    return jsonify({"ok": True})


# ─── Inventário cíclico (EST-006) ──────────────────────────


@api_estoque_bp.post("/api/estoque/inventario/ciclos")
def criar_ciclo():
    data = request.get_json(silent=True) or {}
    deposito_id = data.get("deposito_id")
    nome = data.get("nome")
    if not deposito_id or not nome:
        return jsonify({"error": "deposito_id e nome são obrigatórios", "code": "ciclo_obrigatorio"}), 400
    try:
        return jsonify({"ciclo": inventario_svc.criar_ciclo(int(deposito_id), nome, usuario_id_requisicao())})
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "ciclo_invalido"}), 400


@api_estoque_bp.get("/api/estoque/inventario/ciclos")
def listar_ciclos():
    deposito_id = request.args.get("deposito_id", type=int)
    return jsonify({"ciclos": inventario_svc.listar_ciclos(deposito_id)})


@api_estoque_bp.get("/api/estoque/inventario/ciclos/<int:ciclo_id>")
def detalhe_ciclo(ciclo_id: int):
    ciclo = inventario_svc.detalhe_ciclo(ciclo_id)
    if not ciclo:
        return jsonify({"error": "Ciclo não encontrado", "code": "ciclo_nao_encontrado"}), 404
    return jsonify({"ciclo": ciclo})


@api_estoque_bp.post("/api/estoque/inventario/ciclos/<int:ciclo_id>/contagens")
def registrar_contagem(ciclo_id: int):
    data = request.get_json(silent=True) or {}
    produto_id = data.get("produto_id")
    quantidade_contada = data.get("quantidade_contada")
    if not produto_id or quantidade_contada is None:
        return jsonify({"error": "produto_id e quantidade_contada são obrigatórios", "code": "contagem_obrigatoria"}), 400
    try:
        return jsonify({"contagem": inventario_svc.registrar_contagem(
            ciclo_id, int(produto_id), float(quantidade_contada),
            usuario_id_requisicao(), data.get("observacao"),
        )})
    except (LookupError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "contagem_invalida"}), 400


@api_estoque_bp.post("/api/estoque/inventario/ciclos/<int:ciclo_id>/aprovar")
def aprovar_ciclo(ciclo_id: int):
    try:
        return jsonify({"resultado": inventario_svc.aprovar_ciclo(ciclo_id, usuario_id_requisicao())})
    except (LookupError, ValueError) as exc:
        return jsonify({"error": str(exc), "code": "ciclo_aprovacao_invalida"}), 400


@api_estoque_bp.post("/api/estoque/inventario/ciclos/<int:ciclo_id>/cancelar")
def cancelar_ciclo(ciclo_id: int):
    if not inventario_svc.cancelar_ciclo(ciclo_id):
        return jsonify({"error": "Ciclo não encontrado ou já encerrado", "code": "ciclo_nao_cancelavel"}), 400
    return jsonify({"ok": True})


# ─── Endereçamento (EST-007) ───────────────────────────────


@api_estoque_bp.get("/api/estoque/enderecos")
def listar_enderecos():
    deposito_id = request.args.get("deposito_id", type=int)
    busca = request.args.get("q") or None
    return jsonify({"posicoes": endereco_svc.listar_posicoes(deposito_id or 0, busca)})


@api_estoque_bp.post("/api/estoque/enderecos")
def criar_endereco():
    data = request.get_json(silent=True) or {}
    deposito_id = data.get("deposito_id")
    codigo = data.get("codigo")
    if not deposito_id or not codigo:
        return jsonify({"error": "deposito_id e codigo são obrigatórios", "code": "endereco_obrigatorio"}), 400
    try:
        return jsonify({"posicao": endereco_svc.criar_posicao(int(deposito_id), codigo)})
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "endereco_invalido"}), 400


@api_estoque_bp.delete("/api/estoque/enderecos/<int:posicao_id>")
def excluir_endereco(posicao_id: int):
    try:
        if not endereco_svc.excluir_posicao(posicao_id):
            return jsonify({"error": "Posição não encontrada", "code": "endereco_nao_encontrado"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "endereco_ocupado"}), 400
    return jsonify({"ok": True})


@api_estoque_bp.get("/api/estoque/enderecos/<int:posicao_id>/estoque")
def estoque_endereco(posicao_id: int):
    return jsonify({"itens": endereco_svc.estoque_na_posicao(posicao_id)})


@api_estoque_bp.post("/api/estoque/enderecos/movimentar")
def movimentar_endereco():
    data = request.get_json(silent=True) or {}
    produto_id = data.get("produto_id")
    quantidade = data.get("quantidade")
    de_posicao = data.get("de_posicao_id")
    para_posicao = data.get("para_posicao_id")
    if not produto_id or quantidade is None or (de_posicao is None and para_posicao is None):
        return jsonify({"error": "produto_id, quantidade e ao menos uma posição são obrigatórios", "code": "movimento_endereco_invalido"}), 400
    try:
        return jsonify({"movimento": endereco_svc.movimentar(
            int(de_posicao) if de_posicao else None,
            int(para_posicao) if para_posicao else None,
            int(produto_id),
            float(quantidade),
            usuario_id_requisicao(),
        )})
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "movimento_endereco_invalido"}), 400


@api_estoque_bp.get("/api/estoque/enderecos/primaria/<int:produto_id>")
def endereco_primario(produto_id: int):
    deposito_id = request.args.get("deposito_id", type=int)
    if not deposito_id:
        return jsonify({"error": "deposito_id é obrigatório", "code": "deposito_obrigatorio"}), 400
    return jsonify({"posicao": endereco_svc.posicao_primaria(produto_id, deposito_id)})


@api_estoque_bp.get("/api/estoque/enderecos/movimentos")
def ultimos_movimentos_endereco():
    limit = request.args.get("limit", type=int) or 20
    return jsonify({"movimentos": endereco_svc.ultimos_movimentos(limit)})


# ─── Movimento ─────────────────────────────────────────────

@api_estoque_bp.post("/api/estoque/movimento")
def registrar_movimento():
    data = request.get_json(silent=True) or {}
    deposito_id = data.get("deposito_id")
    produto_id = data.get("produto_id")
    tipo = (data.get("tipo") or "").strip()
    quantidade = float(data.get("quantidade") or 0)

    erros = []
    if not deposito_id:
        erros.append("deposito_id")
    if not produto_id:
        erros.append("produto_id")
    if tipo not in ("entrada", "saida", "ajuste", "transferencia", "inventario"):
        erros.append("tipo inválido")
    if quantidade <= 0:
        erros.append("quantidade deve ser positiva")
    if erros:
        return jsonify({"error": "Campos inválidos: " + ", ".join(erros)}), 400

    # Valida se o produto existe
    with system_conn() as conn:
        if not conn.execute("SELECT 1 FROM produtos_cadastro WHERE id=?", (produto_id,)).fetchone():
            return jsonify({"error": f"Produto {produto_id} não encontrado"}), 404
        if not conn.execute("SELECT 1 FROM depositos WHERE id=?", (deposito_id,)).fetchone():
            return jsonify({"error": f"Depósito {deposito_id} não encontrado"}), 404

    result = estoque_repo.movimentar(
        deposito_id=deposito_id,
        produto_id=produto_id,
        tipo=tipo,
        quantidade=quantidade,
        documento=data.get("documento"),
        observacao=data.get("observacao"),
        lote_id=data.get("lote_id"),
        usuario_id=data.get("usuario_id"),
    )
    # Gatilho contábil (v2.15.0): ajuste de estoque → lançamento quando
    # configurado (default inativo — não altera o comportamento atual).
    if tipo == "ajuste":
        try:
            contabil_gatilhos.disparar(
                "ajuste",
                evento_id=int(result.get("movimento_id") or produto_id),
                valor=quantidade,
                historico=f"Ajuste estoque var {produto_id}",
                origem_tipo="estoque",
            )
        except Exception:
            pass
    return jsonify(result), 201


@api_estoque_bp.get("/api/estoque/movimento")
def listar_movimentos():
    deposito_id = request.args.get("deposito_id", type=int)
    produto_id = request.args.get("produto_id", type=int)
    tipo = request.args.get("tipo") or None
    limit = request.args.get("limit", 100, type=int)
    return jsonify(estoque_repo.movimentos(deposito_id=deposito_id, produto_id=produto_id, tipo=tipo, limit=limit))


# ─── Transferência ─────────────────────────────────────────

@api_estoque_bp.post("/api/estoque/transferir")
def transferir():
    data = request.get_json(silent=True) or {}
    erros = []
    origem_id = data.get("origem_id")
    destino_id = data.get("destino_id")
    produto_id = data.get("produto_id")
    quantidade = float(data.get("quantidade") or 0)
    if not origem_id:
        erros.append("origem_id")
    if not destino_id:
        erros.append("destino_id")
    if not produto_id:
        erros.append("produto_id")
    if quantidade <= 0:
        erros.append("quantidade deve ser positiva")
    if erros:
        return jsonify({"error": "Campos inválidos: " + ", ".join(erros)}), 400
    result = estoque_repo.transferir(
        origem_id, destino_id, produto_id, quantidade, data.get("observacao"), data.get("usuario_id")
    )
    return jsonify(result), 201


# ─── Lotes ─────────────────────────────────────────────────

@api_estoque_bp.get("/api/estoque/lotes")
def listar_lotes():
    deposito_id = request.args.get("deposito_id", type=int)
    produto_id = request.args.get("produto_id", type=int)
    return jsonify(lote_repo.list(deposito_id=deposito_id, produto_id=produto_id))


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
    produto_id = data.get("produto_id")
    codigo = (data.get("codigo") or "").strip()
    if not deposito_id:
        erros.append("deposito_id")
    if not produto_id:
        erros.append("produto_id")
    if not codigo:
        erros.append("codigo")
    if erros:
        return jsonify({"error": "Campos inválidos: " + ", ".join(erros)}), 400
    try:
        lote_id = lote_rastreabilidade.criar_lote(
            int(deposito_id), int(produto_id), codigo,
            quantidade=float(data.get("quantidade") or 0),
            data_fabricacao=data.get("data_fabricacao"),
            data_validade=data.get("data_validade"),
            custo_unitario=float(data["custo_unitario"]) if data.get("custo_unitario") is not None else None,
            fornecedor_id=int(data["fornecedor_id"]) if data.get("fornecedor_id") else None,
            documento=data.get("documento"),
            origem=data.get("origem") or "avulsa",
            observacao=data.get("observacao"),
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "lote_invalido"}), 400
    return jsonify({"id": lote_id}), 201


@api_estoque_bp.post("/api/estoque/lotes/<int:lote_id>/status")
def alterar_status_lote(lote_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("ativo", "bloqueado"):
        return jsonify({"error": "status inválido (ativo|bloqueado)", "code": "status_invalido"}), 400
    if not lote_rastreabilidade.atualizar_status(lote_id, status):
        return jsonify({"error": "Lote não encontrado", "code": "lote_nao_encontrado"}), 404
    return jsonify({"ok": True})


@api_estoque_bp.get("/api/estoque/lotes/fefo")
def consultar_fefo():
    produto_id = request.args.get("produto_id", type=int)
    deposito_id = request.args.get("deposito_id", type=int)
    quantidade = request.args.get("quantidade", type=float)
    if not produto_id or not deposito_id or not quantidade:
        return jsonify({"error": "produto_id, deposito_id e quantidade são obrigatórios", "code": "fefo_obrigatorio"}), 400
    try:
        return jsonify({"alocacao": lote_rastreabilidade.fefo(produto_id, deposito_id, quantidade)})
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "fefo_insuficiente"}), 400


@api_estoque_bp.get("/api/estoque/lotes/recall")
def recall_lote():
    produto_id = request.args.get("produto_id", type=int)
    lote_id = request.args.get("lote_id", type=int)
    if not produto_id:
        return jsonify({"error": "produto_id é obrigatório", "code": "recall_obrigatorio"}), 400
    return jsonify({"itens": lote_rastreabilidade.recall(produto_id, lote_id)})


# ─── ABC histórica (COM-001) ───────────────────────────────


@api_estoque_bp.post("/api/estoque/abc/calcular")
def calcular_abc_historica():
    data = request.get_json(silent=True) or {}
    criterio = data.get("criterio") or "consumo"
    data_inicio = data.get("data_inicio")
    data_fim = data.get("data_fim")
    if not data_inicio or not data_fim:
        return jsonify({"error": "data_inicio e data_fim são obrigatórios", "code": "abc_periodo_obrigatorio"}), 400
    try:
        return jsonify({"calculo": abc_historica.calcular(
            criterio, data_inicio, data_fim,
            int(data["deposito_id"]) if data.get("deposito_id") else None,
            usuario_id_requisicao(),
        )})
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "abc_invalido"}), 400


@api_estoque_bp.post("/api/estoque/abc/<int:calculo_id>/aplicar")
def aplicar_abc_historica(calculo_id: int):
    try:
        return jsonify({"resultado": abc_historica.aplicar(calculo_id)})
    except LookupError as exc:
        return jsonify({"error": str(exc), "code": "abc_nao_encontrado"}), 404


@api_estoque_bp.get("/api/estoque/abc")
def listar_abc_historica():
    deposito_id = request.args.get("deposito_id", type=int)
    return jsonify({"calculos": abc_historica.listar(deposito_id)})


@api_estoque_bp.get("/api/estoque/abc/<int:calculo_id>")
def detalhe_abc_historica(calculo_id: int):
    calc = abc_historica.detalhe(calculo_id)
    if not calc:
        return jsonify({"error": "Cálculo ABC não encontrado", "code": "abc_nao_encontrado"}), 404
    return jsonify({"calculo": calc})


# ─── XYZ e matriz de política (COM-002) ────────────────────


@api_estoque_bp.post("/api/estoque/xyz/calcular")
def calcular_xyz():
    data = request.get_json(silent=True) or {}
    try:
        if data.get("produto_id"):
            return jsonify({"resultado": xyz_svc.classificar(int(data["produto_id"]))})
        return jsonify({"resultado": xyz_svc.calcular_todos()})
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "xyz_invalido"}), 400


@api_estoque_bp.get("/api/estoque/xyz/config")
def obter_xyz_config():
    return jsonify({"config": xyz_svc._config()})


@api_estoque_bp.put("/api/estoque/xyz/config")
def atualizar_xyz_config():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"config": xyz_svc.atualizar_config(
            float(data["cv_x"]), float(data["cv_y"]), int(data["meses_historico"]),
            float(data["intermitente_zeros_pct"]), usuario_id_requisicao(),
        )})
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "xyz_config_invalido"}), 400


@api_estoque_bp.get("/api/estoque/xyz/matriz")
def resumo_matriz_xyz():
    return jsonify({"celulas": xyz_svc.resumo_matriz()})


# ─── Base de demanda (COM-003) ─────────────────────────────


@api_estoque_bp.post("/api/estoque/demanda/consolidar")
def consolidar_demanda():
    data = request.get_json(silent=True) or {}
    deposito_id = data.get("deposito_id")
    return jsonify({"resultado": demanda_svc.consolidar(
        int(deposito_id) if deposito_id else None, usuario_id_requisicao(),
    )})


@api_estoque_bp.post("/api/estoque/demanda")
def registrar_demanda_manual():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"demanda": demanda_svc.registrar_manual(
            int(data["produto_id"]), data["data"], float(data["quantidade"]),
            data.get("observacao"), usuario_id_requisicao(), data.get("chave_manual"),
        )})
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "code": "demanda_invalida"}), 400


@api_estoque_bp.get("/api/estoque/demanda")
def listar_demanda():
    produto_id = request.args.get("produto_id", type=int)
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    return jsonify({"itens": demanda_svc.listar(produto_id, data_inicio, data_fim)})


@api_estoque_bp.get("/api/estoque/demanda/auditar/<int:produto_id>")
def auditar_demanda(produto_id: int):
    return jsonify(demanda_svc.auditar(produto_id))


@api_estoque_bp.post("/api/estoque/demanda/<int:demanda_id>/perdida")
def marcar_demanda_perdida(demanda_id: int):
    data = request.get_json(silent=True) or {}
    try:
        if not demanda_svc.marcar_perdida(demanda_id, data.get("motivo") or ""):
            return jsonify({"error": "Demanda não encontrada", "code": "demanda_nao_encontrada"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "demanda_invalida"}), 400
    return jsonify({"ok": True})


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
            int(dados['deposito_id']), int(dados['produto_id']),
            dados.get('tipo', 'entrada'), float(dados.get('quantidade') or 0),
            idempotency_key=dados.get('idempotency_key'),
            origem_tipo=dados.get('origem_tipo', ''),
            origem_id=dados.get('origem_id'),
            documento=dados.get('documento'), observacao=dados.get('observacao'),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    # Gatilho contábil (v2.15.0): ajuste/inventário → lançamento quando
    # configurado (default inativo — não altera o comportamento atual).
    if not r.get('duplicado') and dados.get('tipo') in ('ajuste', 'inventario'):
        try:
            contabil_gatilhos.disparar(
                'ajuste',
                evento_id=int(r.get('movimento_id') or int(dados['produto_id'])),
                valor=float(dados.get('quantidade') or 0),
                historico=f"Ajuste estoque var {dados['produto_id']} ({dados.get('tipo')})",
                origem_tipo=dados.get('origem_tipo', 'estoque'),
            )
        except Exception:
            pass
    return jsonify(r), 200 if r.get('duplicado') else 201


@api_estoque_bp.post('/api/estoque/reservas')
def reservar_estoque():
    dados = request.get_json(silent=True) or {}
    try:
        r = estoque_repo.movimentar_fato(
            int(dados['deposito_id']), int(dados['produto_id']),
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
            int(dados['deposito_id']), int(dados['produto_id']),
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
    produto_id = int(request.args.get('produto_id', 0))
    if not deposito_id or not produto_id:
        return jsonify({'error': 'informe deposito_id e produto_id'}), 400
    return jsonify(estoque_repo.reconciliar(deposito_id, produto_id))


@api_estoque_bp.get('/api/estoque/reconciliacao/tudo')
def reconciliar_tudo_api():
    dep = request.args.get('deposito_id', type=int)
    return jsonify({'divergencias': estoque_repo.reconciliar_tudo(dep)})


@api_estoque_bp.post('/api/estoque/inventarios')
def lancar_inventario_api():
    dados = request.get_json(silent=True) or {}
    try:
        r = estoque_repo.lancar_inventario(
            int(dados['deposito_id']), int(dados['produto_id']),
            float(dados.get('quantidade_contada') or 0),
            justificativa=dados.get('justificativa', ''),
            idempotency_key=dados.get('idempotency_key'),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(r), 200 if r.get('duplicado') else 201
