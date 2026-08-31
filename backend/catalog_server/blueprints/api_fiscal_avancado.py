import csv, io

from flask import Blueprint, jsonify, request
from catalog_server.db import system_conn
from catalog_server.repositories import emitente_repo, ibpt_repo, nfe_entrada_repo, nfe_saida_repo
from catalog_server.services import ibpt_matcher, nfe_gerador, sefaz_focus
from catalog_server import permissao

api_fiscal_avancado_bp = Blueprint("api_fiscal_avancado", __name__)


@api_fiscal_avancado_bp.post("/api/nfe/emitir/<int:orcamento_id>")
@permissao.exige_permissao("fiscal", "emitir")
def emitir_nfe(orcamento_id: int):
    """Gera o XML (NF-e/NFC-e) a partir do snapshot e armazena em nfe_saida.

    Envia à Focus NFe apenas se `token_focus` estiver configurado; senão a nota
    fica como 'digitada'. Homologação/validação XSD obrigatórias antes de produção.
    """
    dados = request.get_json(silent=True) or {}
    gerado = nfe_gerador.gerar_nfe(
        orcamento_id,
        c_municipio_emit=dados.get("c_municipio_emit", ""),
        c_municipio_dest=dados.get("c_municipio_dest", ""),
        numero=dados.get("numero"),
        serie=dados.get("serie"),
    )
    if not gerado:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    if gerado.get("erro"):
        return jsonify({"error": gerado["erro"]}), 400

    with system_conn() as conn:
        orc = dict(conn.execute("SELECT cliente, total FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone())
    nfe_id = nfe_saida_repo.emitir(
        orcamento_id, gerado["numero"], gerado["serie"], gerado["chave"],
        orc.get("cliente") or "", "", float(orc.get("total") or 0), gerado["xml"],
    )
    emit = emitente_repo.get() or {}
    focus = None
    if emit.get("token_focus"):
        focus = sefaz_focus.enviar(gerado, emit.get("token_focus"), emit.get("ambiente_focus"))
    return jsonify({
        "id": nfe_id, "numero": gerado["numero"], "serie": gerado["serie"],
        "chave": gerado["chave"], "modelo": gerado["modelo"], "ambiente": gerado["ambiente"],
        "focus": focus,
    }), 201


@api_fiscal_avancado_bp.get("/api/emitente")
def get_emitente():
    e = emitente_repo.get()
    return jsonify(e or {})


@api_fiscal_avancado_bp.put("/api/emitente")
def upsert_emitente():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": emitente_repo.upsert(data)})


@api_fiscal_avancado_bp.get("/api/nfe-saida")
def listar_nfe_saida():
    return jsonify(nfe_saida_repo.list(status=request.args.get("status")))


@api_fiscal_avancado_bp.get("/api/nfe-entrada")
def listar_nfe_entrada():
    return jsonify(nfe_entrada_repo.list())


@api_fiscal_avancado_bp.get("/api/ibpt")
def listar_ibpt():
    return jsonify(ibpt_repo.list(ncm=request.args.get("ncm"), limit=request.args.get("limit", 100, type=int)))


@api_fiscal_avancado_bp.post("/api/ibpt")
def upsert_ibpt():
    data = request.get_json(silent=True) or {}
    return jsonify({"id": ibpt_repo.upsert(
        data["ncm"], data.get("descricao", ""),
        float(data.get("aliquota_federal", 0)),
        float(data.get("aliquota_estadual", 0)),
        float(data.get("aliquota_municipal", 0)),
        data.get("fonte", ""),
        data.get("vigencia_inicio"),
        data.get("vigencia_fim"),
    )}), 201


# ─── Sugestões de NCM (IBPT) por produto ───────────────────

@api_fiscal_avancado_bp.get("/api/ibpt/sugestoes")
def listar_sugestoes():
    conf = request.args.get("confianca_min", type=float)
    return jsonify(ibpt_repo.list_sugestoes(
        status=request.args.get("status"),
        q=request.args.get("q"),
        confianca_min=conf,
        limit=request.args.get("limit", 200, type=int),
    ))


@api_fiscal_avancado_bp.post("/api/ibpt/sugestoes/gerar")
def gerar_sugestoes():
    data = request.get_json(silent=True) or {}
    limite = data.get("limite")
    return jsonify(ibpt_matcher.gerar_sugestoes(
        limite=int(limite) if limite else None,
        confianca_min=data.get("confianca_min"),
    ))


@api_fiscal_avancado_bp.post("/api/ibpt/sugestoes/aplicar")
def aplicar_sugestoes():
    data = request.get_json(silent=True) or {}
    return jsonify(ibpt_matcher.aplicar(confianca_min=data.get("confianca_min")))


@api_fiscal_avancado_bp.patch("/api/ibpt/sugestoes/<int:sugestao_id>")
def revisar_sugestao(sugestao_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status == "aplicada":
        ok = ibpt_matcher.aplicar_uma(sugestao_id)
        if not ok:
            return jsonify({"error": "Sugestão não encontrada ou já revisada"}), 404
        return jsonify({"ok": True})
    if status == "rejeitada":
        if not ibpt_repo.set_sugestao_status(sugestao_id, "rejeitada"):
            return jsonify({"error": "Sugestão não encontrada ou já revisada"}), 404
        return jsonify({"ok": True})
    return jsonify({"error": "status inválido"}), 400


@api_fiscal_avancado_bp.get("/api/ibpt/sugestoes/categorias")
def resumo_categorias():
    return jsonify(ibpt_matcher.resumo_categorias())


@api_fiscal_avancado_bp.post("/api/ibpt/aplicar-categoria")
def aplicar_categoria():
    data = request.get_json(silent=True) or {}
    sub_id = data.get("subcategoria_id")
    ncm = data.get("ncm")
    if not sub_id or not ncm:
        return jsonify({"error": "subcategoria_id e ncm obrigatórios"}), 400
    return jsonify(ibpt_matcher.aplicar_por_categoria(int(sub_id), ncm))
