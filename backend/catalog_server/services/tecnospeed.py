"""Integração com a API da Tecnospeed (PlugNotas) para emissão de NFC-e
(modelo 65, consumidor/balcão) e NF-e (modelo 55, B2B).

Baseado na documentação oficial consultada em ago/2026:
- Guia "Primeiros Passos com o PlugNotas":
  https://atendimento.tecnospeed.com.br/hc/pt-br/articles/23715383551767
- Guia de exemplo de payload de NF-e:
  https://atendimento.tecnospeed.com.br/hc/pt-br/articles/12446973447447
- Referência de rotas: https://docs.plugnotas.com.br/#tag/NFe/operation/addNFe

## Pontos-chave do contrato real (diferem de suposições comuns!)

- **Autenticação**: header `x-api-key` com o token da Software House —
  NÃO é `Authorization: Bearer`.
- **URL única**: `https://api.plugnotas.com.br` para tudo. Não existe uma
  URL separada de homologação/produção — o ambiente é uma configuração da
  EMPRESA cadastrada no PlugNotas (`empresa.nfe.config.producao`), não um
  parâmetro do envio da nota.
- **Pré-requisito obrigatório**: a empresa emitente (pelo CNPJ) e o
  certificado digital A1 dela precisam já estar cadastrados no PlugNotas
  (`POST /certificado`, depois `POST /empresa`) ANTES de qualquer emissão
  funcionar. Isso é feito uma vez, não a cada venda.
- **Emissão é assíncrona de verdade**: o `POST /nfe` (ou `/nfce`) NÃO
  devolve a nota autorizada na hora — devolve só um `id` interno do
  PlugNotas. A autorização/rejeição chega depois, via `GET /nfe/{id}`
  (polling) ou webhook. Não existe "autorizado síncrono" na API real.
- **Corpo do envio**: `{"documento": [ {...um ou mais NFes...} ]}` — um
  array, então dá pra emitir várias notas numa chamada.
- **Campos com estrutura aninhada**: `quantidade` e `valorUnitario` de
  cada item são objetos `{comercial, tributavel}`, não números soltos.

## Modo simulado

Por padrão (`tecnospeed_config.simulado = '1'`), nenhuma chamada de rede é
feita. Para não descolar demais do comportamento real (que é assíncrono),
a simulação também começa em "processando" e só "autoriza" na primeira
consulta de status subsequente — assim o fluxo de tela (Caixa → emitir →
acompanhar status) fica realista mesmo sem credenciais.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import requests

from catalog_server.db import system_conn
from catalog_server.repositories import cliente_repo, emitente_repo
from catalog_server.repositories.fiscal_documentos import (
    documento_fiscal_repo,
    tecnospeed_config_repo,
)
from catalog_server.repositories.orcamentos import orcamento_repo

BASE_URL = "https://api.plugnotas.com.br"
TOKEN_SANDBOX = "2da392a6-79d2-4304-a8b7-959572c7e44d"

ENDPOINT_MODELO = {"65": "nfce", "55": "nfe"}

# Meio de pagamento — tabela oficial SEFAZ (tpag), usada tanto por NFC-e
# quanto por NF-e no PlugNotas (campo `meio` dentro de `pagamentos`).
CODIGO_PAGAMENTO_SEFAZ = {
    "dinheiro": "01",
    "cheque": "02",
    "cartao_credito": "03",
    "cartao_debito": "04",
    "credito_loja": "05",
    "vale_alimentacao": "10",
    "vale_refeicao": "11",
    "vale_presente": "12",
    "vale_combustivel": "13",
    "boleto": "15",
    "pix": "17",
    "convenio": "99",
    "outros": "99",
}

# Status devolvidos pela consulta/webhook da PlugNotas, conforme o guia
# "Primeiros Passos" e o artigo "Consultando uma Nota (Resumo NFe)":
# AGENDADO (na fila) -> PROCESSANDO (sendo processada) -> CONCLUIDO
# (autorizada) | REJEITADO | CANCELADO | INTERROMPIDO (parada no meio).
STATUS_MAP = {
    "agendado": "processando",
    "concluido": "autorizado",
    "autorizado": "autorizado",
    "rejeitado": "rejeitado",
    "cancelado": "cancelado",
    "interrompido": "erro",
    "processando": "processando",
    "pendente": "processando",
}


class TecnospeedError(Exception):
    pass


def _headers(token: str) -> dict:
    return {"x-api-key": token, "Content-Type": "application/json"}


def _limpo_doc(doc: str | None) -> str:
    return "".join(ch for ch in (doc or "") if ch.isdigit())


def _pagamentos_do_orcamento(orcamento_id: int) -> list[dict]:
    """Os pagamentos de uma venda ficam em `caixa_movimento` (lançamentos de
    entrada vinculados ao orçamento), não no próprio registro do orçamento."""
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT forma_pagamento, valor FROM caixa_movimento"
            " WHERE orcamento_id=? AND tipo='entrada' ORDER BY id",
            (orcamento_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _snapshot_fiscal_por_item(orcamento_id: int) -> dict[int, dict]:
    """NCM/CFOP/CST/alíquotas gravados no momento da finalização — fonte
    oficial para a nota, não o cadastro atual do produto (que pode ter
    mudado desde a venda)."""
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orcamento_itens_fiscal WHERE orcamento_id=?", (orcamento_id,)
        ).fetchall()
        return {r["item_id"]: dict(r) for r in rows}


def _montar_pagamentos(orcamento: dict) -> list[dict]:
    pagamentos = _pagamentos_do_orcamento(orcamento["id"])
    return [
        {
            "meio": CODIGO_PAGAMENTO_SEFAZ.get(p.get("forma_pagamento", ""), "99"),
            "valor": round(float(p.get("valor") or 0), 2),
        }
        for p in pagamentos
    ] or [{"meio": "99", "valor": round(float(orcamento.get("total") or 0), 2)}]


def _montar_itens(orcamento: dict, regime_simples: bool) -> list[dict]:
    """Monta o grupo `itens` com a estrutura aninhada real do PlugNotas.

    ATENÇÃO — origem dos tributos: usa o snapshot fiscal gravado na
    finalização (`orcamento_itens_fiscal`). Item sem snapshot completo
    (NCM/CFOP/CST ausentes) É REJEITADO PELA SEFAZ DE VERDADE — não existe
    fallback seguro aqui; o item fica sem `tributos` e a chamada vai
    falhar na validação da PlugNotas, de propósito, para não emitir uma
    nota fiscalmente incorreta.
    """
    snapshots = _snapshot_fiscal_por_item(orcamento["id"])
    simulado = tecnospeed_config_repo.simulado()
    itens = []
    for it in orcamento.get("itens", []):
        fiscal = snapshots.get(it.get("id")) or {}
        ncm = fiscal.get("ncm")
        cfop = fiscal.get("cfop")
        if simulado:
            # Em simulação, preenche NCM/CFOP genéricos para não interromper o
            # fluxo quando o produto ainda não tem cadastro fiscal completo.
            ncm = ncm or "00000000"
            cfop = cfop or "5102"
        if not ncm or not cfop:
            raise TecnospeedError(
                f"Item '{it.get('nome')}' não tem NCM/CFOP definidos (snapshot fiscal "
                "ausente). Corrija o cadastro fiscal do produto e refature, ou emita "
                "manualmente."
            )
        qtd = float(it.get("quantidade") or 0)
        preco = float(it.get("preco_unitario") or 0)
        item: dict[str, Any] = {
            "codigo": it.get("sku") or str(it.get("id")),
            "descricao": it.get("nome") or "",
            "ncm": ncm,
            "cfop": cfop,
            "quantidade": {"comercial": qtd, "tributavel": qtd},
            "valorUnitario": {"comercial": round(preco, 4), "tributavel": round(preco, 4)},
            "unidade": {"comercial": "UN", "tributavel": "UN"},
            "total": round(float(it.get("subtotal") or preco * qtd), 2),
        }
        if fiscal.get("cest"):
            item["cest"] = fiscal["cest"]

        icms: dict[str, Any] = {"origem": str(fiscal.get("origem") or 0)}
        if regime_simples and fiscal.get("csosn"):
            icms["csosn"] = fiscal["csosn"]
        else:
            icms["cst"] = fiscal.get("cst_icms") or "102"
        tributos: dict[str, Any] = {"icms": icms}
        if fiscal.get("cst_pis"):
            tributos["pis"] = {"cst": fiscal["cst_pis"]}
        if fiscal.get("cst_cofins"):
            tributos["cofins"] = {"cst": fiscal["cst_cofins"]}
        item["tributos"] = tributos
        itens.append(item)
    return itens


def montar_payload_nfce(orcamento: dict, emitente: dict) -> dict[str, Any]:
    """NFC-e (modelo 65) — venda presencial de balcão, consumidor final,
    normalmente sem destinatário identificado."""
    regime_simples = emitente.get("regime_tributario") == "simples_nacional"
    payload: dict[str, Any] = {
        "idIntegracao": f"orc-{orcamento['id']}-{uuid.uuid4().hex[:8]}",
        "presencial": True,
        "serie": 1,
        "consumidorFinal": True,
        "natureza": "Venda",
        "emitente": {"cpfCnpj": _limpo_doc(emitente.get("cnpj"))},
        "itens": _montar_itens(orcamento, regime_simples),
        "pagamentos": _montar_pagamentos(orcamento),
        "informacoesComplementares": f"Venda ref. orçamento {orcamento.get('numero', '')}",
    }
    cliente_doc = _limpo_doc(orcamento.get("cliente_doc"))
    if cliente_doc:
        payload["destinatario"] = {"cpfCnpj": cliente_doc, "razaoSocial": orcamento.get("cliente") or ""}
    return {"documento": [payload]}


def montar_payload_nfe_b2b(orcamento: dict, emitente: dict, cliente: dict) -> dict[str, Any]:
    """NF-e (modelo 55) — venda B2B faturada, com destinatário identificado
    e endereço/IE completos (exigência real da SEFAZ para NF-e, diferente
    da NFC-e de balcão)."""
    doc_dest = _limpo_doc(cliente.get("doc"))
    if not doc_dest:
        raise TecnospeedError("Cliente sem CPF/CNPJ cadastrado — obrigatório para NF-e.")
    if not cliente.get("c_municipio"):
        raise TecnospeedError(
            "Cliente sem código IBGE do município cadastrado — obrigatório para NF-e "
            "(cadastre em Clientes → editar → endereço)."
        )

    regime_simples = emitente.get("regime_tributario") == "simples_nacional"
    # clientes.contribuinte é um enum de texto: "contribuinte" | "nao_contribuinte"
    contribuinte = cliente.get("contribuinte") == "contribuinte"

    destinatario: dict[str, Any] = {
        "cpfCnpj": doc_dest,
        "razaoSocial": cliente.get("nome") or "",
        # 1 = Contribuinte ICMS, 2 = Isento, 9 = Não Contribuinte (default seguro)
        "indicadorInscricaoEstadual": 1 if contribuinte else 9,
        "endereco": {
            "logradouro": cliente.get("endereco") or "",
            "numero": cliente.get("numero") or "S/N",
            "bairro": cliente.get("bairro") or "",
            "codigoCidade": cliente.get("c_municipio"),
            "descricaoCidade": cliente.get("cidade") or "",
            "estado": cliente.get("uf") or "",
            "cep": _limpo_doc(cliente.get("cep")),
            "codigoPais": "1058",
            "descricaoPais": "Brasil",
        },
    }
    if cliente.get("complemento"):
        destinatario["endereco"]["complemento"] = cliente["complemento"]
    if cliente.get("email"):
        destinatario["email"] = cliente["email"]
    if contribuinte and cliente.get("ie"):
        destinatario["inscricaoEstadual"] = cliente["ie"]

    payload: dict[str, Any] = {
        "idIntegracao": f"orc-{orcamento['id']}-{uuid.uuid4().hex[:8]}",
        "presencial": False,
        "serie": 1,
        "consumidorFinal": not contribuinte,
        "natureza": "Venda",
        "saida": True,
        "finalidade": 1,  # 1 = NF-e normal
        "dataEmissao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "emitente": {"cpfCnpj": _limpo_doc(emitente.get("cnpj"))},
        "destinatario": destinatario,
        "itens": _montar_itens(orcamento, regime_simples),
        "pagamentos": _montar_pagamentos(orcamento),
        "informacoesComplementares": f"Venda ref. orçamento {orcamento.get('numero', '')}",
    }
    return {"documento": [payload]}


def _resposta_simulada(orcamento_id: int) -> dict:
    """Simula a resposta REAL do envio (assíncrona — não vem autorizada na
    hora). O status só vira 'autorizado' numa consulta seguinte, para o
    fluxo de tela ficar parecido com o real (ver `consultar_status`)."""
    return {
        "documents": [{"idIntegracao": f"sim-{orcamento_id}", "id": f"sim-{uuid.uuid4().hex[:20]}"}],
        "message": "Nota(as) em processamento",
        "protocol": f"SIMULADO-{uuid.uuid4().hex[:12]}",
    }


def _emitir(orcamento_id: int, modelo: str) -> dict:
    orc = orcamento_repo.buscar(orcamento_id)
    if orc is None:
        raise TecnospeedError("Orçamento não encontrado")
    if orc.get("status") not in ("faturado", "recebido"):
        raise TecnospeedError(f"Só é possível emitir {'NFC-e' if modelo == '65' else 'NF-e'} para um orçamento faturado/recebido")

    existente = documento_fiscal_repo.get_by_orcamento(orcamento_id, modelo)
    if existente and existente["status"] in ("autorizado", "processando"):
        return existente

    emitente = emitente_repo.get() or {}
    if modelo == "65":
        payload = montar_payload_nfce(orc, emitente)
    else:
        cliente_id = orc.get("cliente_id")
        cliente = cliente_repo.get(cliente_id) if cliente_id else None
        if not cliente:
            raise TecnospeedError(
                "NF-e B2B exige um cliente cadastrado (com CNPJ/CPF, IE e endereço "
                "completo) vinculado ao orçamento — este orçamento não tem cliente_id."
            )
        payload = montar_payload_nfe_b2b(orc, emitente, cliente)

    cfg = tecnospeed_config_repo.get_all()
    doc_id = documento_fiscal_repo.criar_ou_reiniciar(
        orcamento_id, modelo, cfg.get("ambiente", "homologacao"), payload
    )

    if tecnospeed_config_repo.simulado():
        resp = _resposta_simulada(orcamento_id)
    else:
        token = cfg.get("token", "")
        if not token:
            documento_fiscal_repo.atualizar(doc_id, status="erro", motivo="Token da Tecnospeed não configurado")
            raise TecnospeedError(
                "Integração não está em modo simulado, mas não há token configurado "
                "(configure em Configurações → Tecnospeed, ou reative o modo simulado)."
            )
        try:
            r = requests.post(
                f"{BASE_URL}/{ENDPOINT_MODELO[modelo]}",
                json=payload,
                headers=_headers(token),
                timeout=30,
            )
            if r.status_code >= 400:
                erro = r.json().get("error", {}) if r.headers.get("content-type", "").startswith("application/json") else {}
                msg = erro.get("message", f"HTTP {r.status_code}")
                campos = erro.get("data", {}).get("fields")
                if campos:
                    msg += " — " + "; ".join(f"{k}: {v}" for k, v in campos.items())
                documento_fiscal_repo.atualizar(doc_id, status="erro", motivo=msg, resposta_bruta=r.text[:2000])
                raise TecnospeedError(msg)
            resp = r.json()
        except requests.RequestException as e:
            documento_fiscal_repo.atualizar(doc_id, status="erro", motivo=str(e))
            raise TecnospeedError(f"Falha ao comunicar com a Tecnospeed: {e}") from e

    doc_resp = (resp.get("documents") or [{}])[0]
    documento_fiscal_repo.atualizar(
        doc_id,
        status="processando",  # o envio NUNCA vem autorizado na hora — é sempre assíncrono
        tecnospeed_id=doc_resp.get("id"),
        protocolo=resp.get("protocol"),
        resposta_bruta=json.dumps(resp, ensure_ascii=False)[:4000],
    )
    return documento_fiscal_repo.get(doc_id)


def emitir_nfce(orcamento_id: int) -> dict:
    return _emitir(orcamento_id, "65")


def emitir_nfe(orcamento_id: int) -> dict:
    return _emitir(orcamento_id, "55")


def consultar_status(doc_id: int) -> dict:
    """Reconsulta o status na Tecnospeed (emissão é assíncrona — pode levar
    de segundos a minutos até a SEFAZ responder) e atualiza o registro local.

    Formato de resposta confirmado no artigo oficial "Consultando uma Nota
    (Resumo NFe)" — é uma LISTA (mesmo consultando um único id):
    ```
    [{"id":"...", "status":"CONCLUIDO", "chave":"...", "protocolo":"...",
      "numero":"...", "serie":"...", "mensagem":"Autorizado o uso da NF-e",
      "pdf":"...", "xml":"...", "erro": null, ...}]
    ```
    Repare: o campo da chave de acesso é `chave`, não `chaveAcesso`.
    """
    doc = documento_fiscal_repo.get(doc_id)
    if doc is None:
        raise TecnospeedError("Documento fiscal não encontrado")
    if doc["status"] != "processando":
        return doc

    if tecnospeed_config_repo.simulado():
        # Na simulação, a 1ª consulta após o envio já "autoriza" — imita o
        # ciclo real (processando -> autorizado) sem exigir várias chamadas.
        chave_fake = ("SIMULADO" + uuid.uuid4().hex.upper())[:44]
        documento_fiscal_repo.atualizar(
            doc_id, status="autorizado", chave_acesso=chave_fake,
            motivo="Emissão simulada — configure credenciais reais para emitir de verdade.",
        )
        return documento_fiscal_repo.get(doc_id)

    if not doc.get("tecnospeed_id"):
        return doc

    cfg = tecnospeed_config_repo.get_all()
    token = cfg.get("token", "")
    try:
        r = requests.get(
            f"{BASE_URL}/{ENDPOINT_MODELO[doc['modelo']]}/{doc['tecnospeed_id']}",
            headers=_headers(token),
            timeout=30,
        )
        r.raise_for_status()
        resp = r.json()
    except requests.RequestException as e:
        raise TecnospeedError(f"Falha ao consultar status na Tecnospeed: {e}") from e

    # A resposta é uma lista — pega o primeiro (único) resultado.
    dados = resp[0] if isinstance(resp, list) and resp else (resp if isinstance(resp, dict) else {})
    documento_fiscal_repo.atualizar(
        doc_id,
        status=STATUS_MAP.get(str(dados.get("status", "")).lower(), "processando"),
        chave_acesso=dados.get("chave") or doc.get("chave_acesso"),
        numero=dados.get("numero"),
        serie=dados.get("serie"),
        motivo=dados.get("erro") or dados.get("mensagem"),
        xml_url=dados.get("xml") or doc.get("xml_url"),
        danfe_url=dados.get("pdf") or doc.get("danfe_url"),
        resposta_bruta=json.dumps(resp, ensure_ascii=False)[:4000],
    )
    return documento_fiscal_repo.get(doc_id)


def processar_webhook(payload: dict) -> None:
    """Recebe notificações assíncronas de mudança de status. Segundo a
    doc oficial, o corpo do webhook segue o MESMO schema da consulta
    resumida (`chave`, `mensagem`, `erro`, `pdf`, `xml`...), só acrescido
    do campo `documento` para identificação. Só dispara em status finais
    (CONCLUIDO, REJEITADO, CANCELADO, INTERROMPIDO) — nunca PROCESSANDO."""
    tecnospeed_id = payload.get("id") or payload.get("idIntegracao")
    if not tecnospeed_id:
        return
    doc = documento_fiscal_repo.get_by_tecnospeed_id(tecnospeed_id)
    if doc is None:
        return
    documento_fiscal_repo.atualizar(
        doc["id"],
        status=STATUS_MAP.get(str(payload.get("status", "")).lower(), doc["status"]),
        chave_acesso=payload.get("chave") or doc.get("chave_acesso"),
        numero=payload.get("numero") or doc.get("numero"),
        serie=payload.get("serie") or doc.get("serie"),
        motivo=payload.get("erro") or payload.get("mensagem"),
        xml_url=payload.get("xml") or doc.get("xml_url"),
        danfe_url=payload.get("pdf") or doc.get("danfe_url"),
        resposta_bruta=json.dumps(payload, ensure_ascii=False)[:4000],
    )


# ─── Cadastro de empresa/certificado (setup único, não por venda) ────────

def cadastrar_certificado(arquivo_bytes: bytes, senha: str, email: str = "") -> dict:
    """POST /certificado — precisa ser feito uma vez por CNPJ emitente,
    antes de qualquer emissão funcionar. Certificado A1 (.pfx/.p12)."""
    cfg = tecnospeed_config_repo.get_all()
    token = cfg.get("token", "")
    if not token:
        raise TecnospeedError("Configure o token da Tecnospeed antes de cadastrar o certificado")
    try:
        r = requests.post(
            f"{BASE_URL}/certificado",
            headers={"x-api-key": token},
            files={"arquivo": ("certificado.pfx", arquivo_bytes)},
            data={"senha": senha, "email": email},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise TecnospeedError(f"Falha ao cadastrar certificado: {e}") from e


def cadastrar_empresa(dados_empresa: dict) -> dict:
    """POST /empresa — cadastra o CNPJ emitente no PlugNotas (uma vez).
    `dados_empresa` deve seguir o formato documentado (cpfCnpj, razaoSocial,
    endereco, nfe.config, nfce.config, etc. — ver TECNOSPEED.md)."""
    cfg = tecnospeed_config_repo.get_all()
    token = cfg.get("token", "")
    if not token:
        raise TecnospeedError("Configure o token da Tecnospeed antes de cadastrar a empresa")
    try:
        r = requests.post(
            f"{BASE_URL}/empresa",
            json=dados_empresa,
            headers=_headers(token),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise TecnospeedError(f"Falha ao cadastrar empresa: {e}") from e
