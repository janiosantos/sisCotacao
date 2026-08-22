"""Resolvedor de regra fiscal vigente.

Seleciona, da matriz `fiscal_regra`, a regra que casa com o contexto da
operação E que possui uma versão válida na data informada.

Critérios vazios ('') na regra significam "qualquer valor". `prioridade` menor
vence. Se nenhuma regra casar, retorna None — o chamador deve tratar como
`FISCAL_RULE_NOT_FOUND` (nunca escolher um padrão automaticamente).

Este é o bloco de construção do `FiscalRuleEngine` (FASE 3). Aqui não se
calcula tributo; apenas se resolve qual regra se aplica.
"""
from __future__ import annotations

from datetime import date

from catalog_server.db import system_conn


def _vigente(inicio: str, fim: str | None, data: str) -> bool:
    return (inicio or "") <= data and (not fim or data <= fim)


def _casa(regra: dict, contexto: dict, data: str) -> bool:
    if not regra.get("ativo"):
        return False
    for campo, valor_ctx in (
        ("regime", contexto.get("regime")),
        ("uf_origem", contexto.get("uf_origem")),
        ("uf_destino", contexto.get("uf_destino")),
        ("tipo_cliente", contexto.get("tipo_cliente")),
        ("contribuinte", contexto.get("contribuinte")),
        ("finalidade", contexto.get("finalidade")),
        ("modelo_documento", contexto.get("modelo_documento")),
        ("natureza_operacao", contexto.get("natureza_operacao")),
        ("cest", contexto.get("cest")),
        ("origem", str(contexto.get("origem") or "")),
    ):
        exigido = (regra.get(campo) or "").strip()
        valor_ctx = (valor_ctx or "").strip()
        if exigido and exigido != valor_ctx:
            return False
    ncm_prefixo = (regra.get("ncm_prefixo") or "").strip()
    ncm = (contexto.get("ncm") or "").strip()
    if ncm_prefixo and not ncm.startswith(ncm_prefixo):
        return False
    return True


def buscar_regra(contexto: dict, data: str | None = None, dimensao: str | None = None) -> dict | None:
    """Regra ativa que casa com o contexto e tem versão válida em `data`.

    `dimensao` em ('operacao','produto') restringe a busca à dimensão (incluindo
    'geral' como compatibilidade). Sem `dimensao`, busca qualquer regra.
    """
    data = data or date.today().isoformat()
    dimensoes = {
        "operacao": ("operacao", "geral"),
        "produto": ("produto", "geral"),
        "geral": ("geral",),
    }
    with system_conn() as conn:
        sql = "SELECT * FROM fiscal_regra WHERE ativo=1"
        args: list = []
        if dimensao:
            if dimensao not in dimensoes:
                return None
            sql += " AND dimensao IN (" + ", ".join("?" for _ in dimensoes[dimensao]) + ")"
            args.extend(dimensoes[dimensao])
        sql += " ORDER BY prioridade, id"
        regras = [dict(r) for r in conn.execute(sql, args).fetchall()]
        for regra in regras:
            if not _casa(regra, contexto, data):
                continue
            versao = conn.execute(
                "SELECT * FROM fiscal_regra_versao"
                " WHERE regra_id=? AND status='ativa' AND data_inicio<=? AND (data_fim IS NULL OR data_fim>=?)"
                " ORDER BY data_inicio DESC LIMIT 1",
                (regra["id"], data, data),
            ).fetchone()
            if versao is None:
                continue
            resultado = dict(regra)
            resultado["versao"] = dict(versao)
            return resultado
    return None
