from __future__ import annotations

from catalog_server.config import COTACAO_STATUSES


def status_label(status: str) -> str:
    return {
        "aberta": "Aberta",
        "fechada": "Fechada",
        "cancelada": "Cancelada",
        "pendente": "Pendente",
        "analise": "Pronta para Analisar",
        "finalizada": "Finalizada",
        "respondido": "Respondido",
    }.get(status, status)


def valid_status(status: str) -> bool:
    return status in COTACAO_STATUSES


def fmt_brl(value: float | None) -> str:
    if value is None:
        return "R$ 0,00"
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def document_context(cotacao: dict, itens: list[dict], fornecedores: list[dict], vencedores: list[dict], precos: list[dict] | None = None) -> dict:
    vencedor_map = {
        v["cotacao_item_id"]: v for v in vencedores
    }
    fornecedor_nome = {f["fornecedor_id"]: f["nome"] for f in fornecedores}
    preco_vencedor = {
        (v["fornecedor_id"], v["cotacao_item_id"]): p
        for p in (precos or [])
        for v in [vencedor_map.get(p["cotacao_item_id"])]
        if v and v["fornecedor_id"] == p["fornecedor_id"]
    }
    for item in itens:
        v = vencedor_map.get(item["cotacao_item_id"])
        if v:
            item["vencedor"] = fornecedor_nome.get(v["fornecedor_id"], "—")
            item["vencedor_preco"] = v["preco_unitario"]
            vp = preco_vencedor.get((v["fornecedor_id"], item["cotacao_item_id"]))
            item["vencedor_unidade"] = (vp or {}).get("unidade_compra") or ""
            item["vencedor_fator"] = float((vp or {}).get("fator_conversao") or 0)
    return {
        "number": cotacao["numero"],
        "titulo": cotacao["titulo"],
        "cliente": cotacao["cliente"],
        "observacoes": cotacao["observacoes"],
        "status": cotacao["status"],
        "status_label": status_label(cotacao["status"]),
        "criado_em": cotacao["criado_em"],
        "fechado_em": cotacao.get("fechado_em"),
        "itens": itens,
        "total": sum(float(i.get("vencedor_preco", 0) or 0) * float(i["quantidade"]) for i in itens),
    }
