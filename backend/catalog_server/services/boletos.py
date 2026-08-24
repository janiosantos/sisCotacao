"""Boletos de vendas a prazo (v2.22.0).

Sem integração bancária real nesta fase: gera o layout de boleto imprimível
(linha digitável 48 dígitos + código de barras) com dados da conta a receber
e o número do documento (orçamento). O boleto é marcado na conta e o pedido
finalizado com boleto emitido não pode ser alterado/reaberto.
"""
from __future__ import annotations

import hashlib

from catalog_server.db import system_conn

# Status possíveis do boleto na conta a receber.
STATUS_NAO_EMITIDO = "nao_emitido"
STATUS_GERADO = "gerado"
STATUS_IMPRESSO = "impresso"
STATUS_CANCELADO = "cancelado"


def _linha_digitavel(conta: dict) -> str:
    """Gera uma linha digitável de 48 dígitos (formato genérico).

    Composta por: banco (3) + moeda (1) + identificador do documento + DV.
    Não é um boleto de um banco real — serve para o fluxo até a integração.
    """
    chave = f"{conta['documento'] or ''}|{conta['id']}|{conta['valor']:.2f}"
    digest = hashlib.sha1(chave.encode("utf-8")).hexdigest()
    num = "".join(c for c in digest if c.isdigit())
    base = "0019" + num[:16] + str(conta["id"])[:9].rjust(9, "0")
    return (base[:43] + "0" + base[43:])[:48].ljust(48, "0")


def _codigo_barras(conta: dict) -> str:
    return _linha_digitavel(conta)[:44]


def gerar_boleto(conta_id: int) -> dict | None:
    """Marca a conta com um boleto gerado e devolve os dados para o template."""
    with system_conn() as conn:
        conta = conn.execute(
            "SELECT * FROM contas_receber WHERE id=?", (conta_id,)
        ).fetchone()
        if conta is None:
            return None
        linha = _linha_digitavel(dict(conta))
        codigo = _codigo_barras(dict(conta))
        nosso_numero = f"{int(conta['id']):08d}-1"
        conn.execute(
            "UPDATE contas_receber SET status_boleto=?, linha_digitavel=?,"
            " codigo_barras=?, nosso_numero=? WHERE id=?",
            (STATUS_GERADO, linha, codigo, nosso_numero, conta_id),
        )
        d = dict(conta)
        d.update({
            "status_boleto": STATUS_GERADO,
            "linha_digitavel": linha,
            "codigo_barras": codigo,
            "nosso_numero": nosso_numero,
        })
        return d


def gerar_boletos_parcelas(documento: str) -> list[dict]:
    """Gera boletos para todas as parcelas (contas a receber) de um documento."""
    with system_conn() as conn:
        contas = conn.execute(
            "SELECT * FROM contas_receber WHERE documento=? ORDER BY id",
            (documento,),
        ).fetchall()
    boletos = []
    for c in contas:
        b = gerar_boleto(c["id"])
        if b:
            boletos.append(b)
    return boletos


def tem_boleto_emitido(documento: str) -> bool:
    """True se alguma conta do documento tem boleto gerado/impresso."""
    if not documento:
        return False
    with system_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM contas_receber WHERE documento=? AND status_boleto IN (?,?) LIMIT 1",
            (documento, STATUS_GERADO, STATUS_IMPRESSO),
        ).fetchone()
        return row is not None


def parcelas_com_boleto(documento: str) -> list[dict]:
    """Parcelas do documento com dados de boleto (para o pedido)."""
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM contas_receber WHERE documento=? ORDER BY id",
            (documento,),
        ).fetchall()]