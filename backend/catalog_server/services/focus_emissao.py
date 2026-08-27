"""Emissão NFC-e/NF-e via Focus NFe — monta payload do orçamento e usa o
adapter (`focus_adapter`). Alternativa ao provedor TecnoSpeed.

Payload mínimo Focus v2 (layout resumido): itens com ncm/cfop/csosn/valor,
tomador quando informado. Campos complementares entram conforme regra v2.
"""
from __future__ import annotations

from catalog_server import flags
from catalog_server.db import system_conn
from catalog_server.fiscal.snapshot import montar_contextos_orcamento
from catalog_server.repositories.fiscal_documentos import (
    documento_fiscal_repo,
    tecnospeed_config_repo,
)
from catalog_server.services import focus_adapter


class FocusEmissaoError(Exception):
    pass


def _emitente() -> dict:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT * FROM emitente WHERE ativo=1 LIMIT 1"
        ).fetchone()
        return dict(row) if row else {}


def _itens_payload(orcamento_id: int) -> list[dict]:
    itens: list[dict] = []
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orcamento_itens WHERE orcamento_id=? ORDER BY id",
            (orcamento_id,),
        ).fetchall()
    for idx, it in enumerate(rows, start=1):
        vid = it["produto_id"]
        perfil = {}
        with system_conn() as conn:
            pf = conn.execute(
                "SELECT * FROM product_fiscal_profile WHERE produto_id=?",
                (vid,),
            ).fetchone()
            perfil = dict(pf) if pf else {}

        ctx_dados = {
            "product_id": vid,
            "operation_type": "venda",
            "quantity": str(it["quantidade"]),
            "unit_price": str(it["preco_unitario"]),
        }
        result = None
        for _ctx, res in montar_contextos_orcamento(orcamento_id):
            if _ctx.get("product_id") == vid if isinstance(_ctx, dict) else False:
                result = res
                break

        itens.append(
            {
                "numero_item": idx,
                "codigo_produto": it["sku"] or str(vid),
                "descricao": it["nome"],
                "ncm": perfil.get("ncm", ""),
                "cfop": (result.cfop if result else "") or "",
                "csosn": (result.csosn if result else "") or perfil.get("cest", "") and "" or "",
                "quantidade_comercial": float(it["quantidade"]),
                "valor_unitario_comercial": float(it["preco_unitario"]),
                "valor_total_bruto": float(it["subtotal"] or 0),
            }
        )
    return itens


def emitir(orcamento_id: int, modelo: str) -> dict:
    """Emite NFC-e (65) ou NF-e (55) do orçamento via Focus NFe."""
    cfg = tecnospeed_config_repo.get_all()
    token = cfg.get("token") or ""
    ambiente = cfg.get("ambiente") or "homologacao"
    if not token:
        raise FocusEmissaoError("Token Focus não configurado")

    ref = f"orc-{orcamento_id}-{modelo}"
    payload: dict = {
        "id": ref,
        "natureza_operacao": "VENDA",
        "modelo_documento": modelo,
        "finalidade_emissao": "1",
        "itens": _itens_payload(orcamento_id),
    }
    emit = _emitente()
    if emit:
        payload.update(
            {
                "cnpj_emitente": emit.get("cnpj", ""),
                "nome_emitente": emit.get("razao_social", ""),
                "uf_emitente": emit.get("uf", ""),
                "inscricao_estadual_emitente": emit.get("ie", ""),
                "regime_especial_tributacao": (
                    "6" if "simples" in (emit.get("regime_tributario") or "") else ""
                ),
            }
        )

    resposta = focus_adapter.emitir(
        ambiente=ambiente,
        token=token,
        modelo=modelo,
        payload=payload,
        referencia_externa=ref,
    )
    status_focus = (resposta.get("status") or "").lower()
    cstat = str(resposta.get("cStatus") or resposta.get("status") or "")
    autorizado = status_focus == "autorizado" or cstat in ("100", "150")

    doc_id = documento_fiscal_repo.criar_ou_reiniciar(
        orcamento_id, modelo, ambiente, payload
    )
    if autorizado:
        resposta_bruta = focus_adapter.consultar(
            ambiente=ambiente, token=token, modelo=modelo,
            referencia_externa=ref,
        )
        documento_fiscal_repo.atualizar(
            doc_id, status="autorizado",
            protocolo=str(resposta.get("protocolo") or ""),
            chave_acesso=str(resposta.get("chave_nfe") or ""),
            numero=str(resposta.get("numero") or ""),
            serie=str(resposta.get("serie") or ""),
            resposta_bruta=__import__("json").dumps(resposta, ensure_ascii=False)[:20000],
        )
    doc = dict(documento_fiscal_repo.get_by_orcamento(orcamento_id, modelo) or {})
    doc["id"] = doc_id
    doc["referencia_focus"] = ref
    return doc


def consultar(orcamento_id: int, modelo: str) -> dict:
    doc = documento_fiscal_repo.get_by_orcamento(orcamento_id, modelo)
    if doc is None or not doc.get("referencia_focus"):
        # compat: referência derivada do padrão de emissão
        doc = doc or {"orcamento_id": orcamento_id}
        doc["referencia_focus"] = f"orc-{orcamento_id}-{modelo}"
    cfg = tecnospeed_config_repo.get_all()
    return focus_adapter.consultar(
        ambiente=cfg.get("ambiente") or "homologacao",
        token=cfg.get("token") or "",
        modelo=modelo,
        referencia_externa=doc["referencia_focus"],
    )
