"""API de orçamentos de venda ao cliente (PDV)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from catalog_server.repositories.orcamentos import STATUS_LIST, orcamento_repo
from catalog_server.repositories.pdv_frete import desconto_repo, frete_repo
from catalog_server.repositories.financeiro import contas_repo
from catalog_server.repositories.estoque import estoque_repo

api_orcamentos_bp = Blueprint("api_orcamentos", __name__)


@api_orcamentos_bp.get("/api/orcamentos")
def listar():
    status = (request.args.get("status") or "").strip()
    return jsonify(orcamento_repo.listar(status))


@api_orcamentos_bp.post("/api/orcamentos")
def criar():
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not itens:
        return jsonify({"error": "O orçamento precisa de ao menos 1 item"}), 400
    orcamento_id, numero = orcamento_repo.criar(
        cliente=data.get("cliente") or "",
        contato=data.get("contato") or "",
        validade_dias=data.get("validade_dias") or 7,
        observacoes=data.get("observacoes") or "",
        desconto=data.get("desconto") or 0,
        itens=itens,
        frete=float(data.get("frete") or 0),
        seguro=float(data.get("seguro") or 0),
        despesas_acessorias=float(data.get("despesas_acessorias") or 0),
        status=data.get("status", "rascunho"),
        condicao_pagamento_id=data.get("condicao_pagamento_id"),
    )
    return jsonify({"id": orcamento_id, "numero": numero}), 201


@api_orcamentos_bp.get("/api/orcamentos/<int:orcamento_id>")
def buscar(orcamento_id: int):
    orcamento = orcamento_repo.buscar(orcamento_id)
    if orcamento is None:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    return jsonify(orcamento)


@api_orcamentos_bp.patch("/api/orcamentos/<int:orcamento_id>")
def atualizar(orcamento_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status is not None and status not in STATUS_LIST:
        return jsonify({"error": "Status inválido"}), 400
    if not orcamento_repo.atualizar_cabecalho(
        orcamento_id,
        cliente=data.get("cliente"),
        contato=data.get("contato"),
        validade_dias=data.get("validade_dias"),
        observacoes=data.get("observacoes"),
        status=status,
        desconto=data.get("desconto"),
    ):
        return jsonify({"error": "Orçamento não encontrado"}), 404

    # Gatilho: faturar → gerar conta a receber + baixar estoque
    if status == "faturado":
        from datetime import datetime, timedelta
        from catalog_server.db import system_conn as _sc
        orc = orcamento_repo.buscar(orcamento_id)
        if orc:
            venc = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            try:
                contas_repo.criar_receber(
                    cliente=orc.get("cliente", "") or "",
                    valor=float(orc.get("total") or 0),
                    data_vencimento=venc,
                    descricao=f"Venda {orc.get('numero', '')}",
                    documento=orc.get("numero", ""),
                )
            except Exception:
                pass

            for item in orc.get("itens", []):
                qtd = float(item.get("quantidade") or 0)
                if qtd <= 0:
                    continue
                vid = item.get("variante_id")
                if not vid:
                    pid = item.get("produto_id")
                    if pid:
                        row = _sc().execute(
                            "SELECT id FROM variantes WHERE produto_id=? AND ativo=1 LIMIT 1",
                            (pid,),
                        ).fetchone()
                        vid = row["id"] if row else None
                if vid:
                    try:
                        estoque_repo.movimentar(
                            deposito_id=1, variante_id=vid,
                            tipo="saida", quantidade=qtd,
                            documento=orc.get("numero", ""),
                        )
                    except Exception:
                        pass

    return jsonify({"ok": True})


@api_orcamentos_bp.put("/api/orcamentos/<int:orcamento_id>/itens")
def substituir_itens(orcamento_id: int):
    data = request.get_json(silent=True) or {}
    itens = data.get("itens") or []
    if not orcamento_repo.substituir_itens(orcamento_id, itens):
        return jsonify({"error": "Orçamento não encontrado"}), 404
    return jsonify({"ok": True})


@api_orcamentos_bp.delete("/api/orcamentos/<int:orcamento_id>")
def excluir(orcamento_id: int):
    if not orcamento_repo.excluir(orcamento_id):
        return jsonify({"error": "Orçamento não encontrado"}), 404
    return jsonify({"ok": True})


# ─── Políticas ─────────────────────────────────────────────

@api_orcamentos_bp.get("/api/politica-descontos")
def listar_politica_descontos():
    return jsonify(desconto_repo.list())


@api_orcamentos_bp.post("/api/politica-descontos")
def criar_politica_desconto():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": desconto_repo.create(
        data.get("nome", ""), data.get("tipo", "percentual"),
        float(data.get("valor_maximo") or 0),
        float(data.get("valor_minimo") or 0),
        data.get("perfil", ""),
    )}), 201


@api_orcamentos_bp.get("/api/politica-fretes")
def listar_politica_fretes():
    uf = request.args.get("uf") or None
    return jsonify(frete_repo.list(uf=uf))


@api_orcamentos_bp.post("/api/politica-fretes")
def criar_politica_frete():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": frete_repo.create(
        data.get("nome", ""), data.get("uf", ""),
        float(data.get("valor_frete") or 0),
        float(data.get("valor_minimo_pedido") or 0),
        data.get("tipo", "fixo"),
    )}), 201