"""Helpers do fluxo de compras: links públicos por token e mensagens padrão
de WhatsApp/e-mail para o fornecedor convidado.
"""
from __future__ import annotations

import math
import os
import re
from urllib.parse import quote

from flask import request

from catalog_server.repositories import catalog_repo, compras_repo


def montar_matriz(cotacao_id: int) -> dict | None:
    dados = compras_repo.comparar(cotacao_id)
    if dados is None:
        return None
    produtos = catalog_repo.products_by_ids([i["produto_id"] for i in dados["itens"]])
    itens = []
    for it in dados["itens"]:
        p = produtos.get(it["produto_id"], {})
        precos = {}
        melhor_id = None
        melhor_preco = None
        melhor_prazo_id = None
        melhor_prazo = None
        for pr in dados["precos"]:
            if pr["cotacao_item_id"] != it["cotacao_item_id"]:
                continue
            desc = float(pr["desconto"] or 0)
            preco_liquido = float(pr["preco_unitario"]) * (1 - desc / 100.0)
            disponivel = bool(pr["disponibilidade_estoque"])
            prazo = pr["prazo_entrega_dias"]
            fator = float(pr.get("fator_conversao") or 1)
            fator = fator if fator and fator > 0 else 1
            unidade = (pr.get("unidade_compra") or "").strip() or "UN"
            motivo = (pr.get("motivo_indisponibilidade") or "").strip()
            qtd = float(it["quantidade"] or 0)
            precos[str(pr["fornecedor_id"])] = {
                "preco": float(pr["preco_unitario"]),
                "desconto": desc,
                "preco_liquido": preco_liquido,
                "prazo": prazo,
                "disponivel": disponivel,
                "unidade_compra": unidade,
                "fator_conversao": fator,
                "marca_ofertada": (pr.get("marca_ofertada") or "").strip(),
                "motivo_indisponibilidade": motivo,
                "preco_embalagem": round(preco_liquido * fator, 4),
                "qtd_embalagens": math.ceil(qtd / fator) if qtd > 0 else 0,
            }
            if disponivel and preco_liquido > 0 and (melhor_preco is None or preco_liquido < melhor_preco):
                melhor_preco = preco_liquido
                melhor_id = pr["fornecedor_id"]
            if disponivel and preco_liquido > 0 and prazo is not None and (melhor_prazo is None or prazo < melhor_prazo):
                melhor_prazo = prazo
                melhor_prazo_id = pr["fornecedor_id"]
        itens.append({
            "cotacao_item_id": it["cotacao_item_id"],
            "produto_id": it["produto_id"],
            "quantidade": it["quantidade"],
            "descricao": it.get("descricao") or "",
            "name": it.get("descricao") or p.get("name", f"Produto #{it['produto_id']}"),
            "sku": p.get("sku", ""),
            "brand": p.get("brand", ""),
            "imagem_url": p.get("imagem_url"),
            "precos": precos,
            "melhor_id": melhor_id,
            "melhor_preco": melhor_preco,
            "melhor_prazo_id": melhor_prazo_id,
            "melhor_prazo": melhor_prazo,
        })

    # Lote centralizado: fornecedor único que precificou TODOS os itens com o menor total.
    centralizado = None
    n_itens = len(itens)
    if n_itens:
        suppliers = [f for f in dados["fornecedores"] if f["status"] == "respondido"]
        for fornecedor in suppliers:
            fid = fornecedor["fornecedor_id"]
            cobertos = [i for i in itens if str(fid) in i["precos"]
                        and i["precos"][str(fid)]["disponivel"]
                        and i["precos"][str(fid)]["preco_liquido"] > 0]
            if len(cobertos) != n_itens:
                continue
            total = sum(i["precos"][str(fid)]["preco_liquido"] * i["quantidade"] for i in cobertos)
            if centralizado is None or total < centralizado["total"]:
                centralizado = {"fornecedor_id": fid, "nome": fornecedor["nome"],
                                "total": total, "n_itens": n_itens}

    result_txt = {
        "cotacao": dados["cotacao"],
        "logica": "fracionado",
        "itens": itens,
        "fornecedores": dados["fornecedores"],
        "centralizado": centralizado,
    }
    return result_txt


def base_url_for() -> str:
    """URL pública base usada nos links de convite ao fornecedor.

    Prioriza `PUBLIC_BASE_URL` (variável de ambiente) — necessária quando o
    acesso externo passa por redirecionamento de porta (ex.: CGNAT redireciona
    `:6173` para a porta 80 do nginx), pois `request.host_url` reflete o Host
    interno/LAN e geraria links sem a porta pública. Sem a variável, usa o Host
    da requisição.
    """
    public = os.getenv("PUBLIC_BASE_URL", "").strip()
    if public:
        return public.rstrip("/")
    return request.host_url.rstrip("/")


def fornecedor_link(token: str) -> str:
    return f"{base_url_for()}/fornecedor/{token}"


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def whatsapp_url(whatsapp: str | None, texto: str) -> str:
    num = _digits(whatsapp)
    if not num:
        return ""
    if not num.startswith("55") and len(num) in (10, 11):
        num = "55" + num
    return f"https://wa.me/{num}?text={quote(texto)}"


def mailto_url(email: str | None, assunto: str, corpo: str) -> str:
    if not email:
        return ""
    return (f"mailto:{quote(email)}?subject={quote(assunto)}"
            f"&body={quote(corpo)}")


def mensagem_whatsapp(comprador: str, fornecedor: str | None, link: str,
                      apelido: str | None, data_limite: str | None) -> str:
    rep = fornecedor or "Equipe"
    trecho_limite = f" Preferimos receber até {data_limite}." if data_limite else ""
    ap = f' sobre a cotação "{apelido}"' if apelido else ""
    return (
        f"Olá, {rep}! Aqui é o {comprador}. Estamos cotando alguns itens para nossa loja{ap}."
        f" Você pode preencher seus preços diretamente neste link seguro? Não precisa de login:"
        f" {link}{trecho_limite} Obrigado!"
    )


def email_assunto(apelido: str | None, numero: str | None) -> str:
    ap = apelido or f"Cotação {numero or ''}".strip()
    return f"Cotação para cotação de preços — {ap}"


def email_corpo(comprador: str, fornecedor: str | None, link: str,
                apelido: str | None, data_limite: str | None) -> str:
    msg = mensagem_whatsapp(comprador, fornecedor, link, apelido, data_limite)
    msg += ("\n\nEste e-mail foi gerado automaticamente. Utilize o link para "
            "informar seus preços de forma segura, sem necessidade de login.")
    return msg