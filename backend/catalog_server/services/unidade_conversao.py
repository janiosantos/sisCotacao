"""Conversões de unidade por produto/embalagem (MDM-002).

Fornece o cadastro versionado de conversões (ex.: 1 CX = N UN) com unidade base,
resolução de conversão (converter) e fallback para os campos legados
`produtos_cadastro.unidade_venda`/`fator_conversao` enquanto a migração não os
substitui. Apenas Expand: não altera o contrato atual de unidades.
"""

from __future__ import annotations

from decimal import Decimal

from catalog_server.db import system_conn

_COLUNAS = (
    "id, produto_id, unidade_origem, unidade_destino, fator, unidade_base, "
    "ativo, versao, criado_em, atualizado_em"
)


def listar(produto_id: int) -> list[dict]:
    with system_conn() as conn:
        rows = conn.execute(
            f"SELECT {_COLUNAS} FROM unidade_conversao "
            "WHERE produto_id=? AND ativo ORDER BY unidade_origem",
            (produto_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def obter(produto_id: int, origem: str) -> dict | None:
    with system_conn() as conn:
        r = conn.execute(
            f"SELECT {_COLUNAS} FROM unidade_conversao "
            "WHERE produto_id=? AND unidade_origem=? AND ativo",
            (produto_id, origem),
        ).fetchone()
        return dict(r) if r else None


def salvar(
    produto_id: int,
    origem: str,
    destino: str,
    fator: float,
    base: str,
    usuario_id: int | None,
) -> dict:
    """Cria/atualiza a conversão ativa (origem→destino). Desativa a anterior
    (auditoria por versão). `fator` = quantas unidades de `destino` equivalem a
    1 unidade de `origem`."""
    origem = (origem or "").strip().upper()
    destino = (destino or "").strip().upper()
    base = (base or "").strip().upper()
    if not origem or not destino or not base:
        raise ValueError("unidade_origem, unidade_destino e unidade_base são obrigatórias")
    if origem == destino:
        raise ValueError("unidade_origem e unidade_destino devem ser diferentes")
    try:
        fator_dec = Decimal(str(fator))
    except (TypeError, ValueError):
        raise ValueError("fator inválido") from None
    if fator_dec <= 0:
        raise ValueError("fator deve ser maior que zero")
    with system_conn() as conn:
        ativo = conn.execute(
            "SELECT id, versao FROM unidade_conversao "
            "WHERE produto_id=? AND unidade_origem=? AND ativo",
            (produto_id, origem),
        ).fetchone()
        nova_versao = int(ativo["versao"]) + 1 if ativo else 1
        if ativo:
            conn.execute(
                "UPDATE unidade_conversao SET ativo=FALSE, atualizado_em=NOW() WHERE id=?",
                (ativo["id"],),
            )
        novo_id = conn.execute(
            "INSERT INTO unidade_conversao "
            "(produto_id, unidade_origem, unidade_destino, fator, unidade_base, "
            "ativo, versao, criado_por) "
            "VALUES (?,?,?,?,?,TRUE,?,?) RETURNING id",
            (produto_id, origem, destino, fator_dec, base, nova_versao, usuario_id),
        ).fetchone()["id"]
        r = conn.execute(
            f"SELECT {_COLUNAS} FROM unidade_conversao WHERE id=?",
            (novo_id,),
        ).fetchone()
        return dict(r)


def excluir(produto_id: int, origem: str, usuario_id: int | None) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE unidade_conversao SET ativo=FALSE, atualizado_em=NOW() "
            "WHERE produto_id=? AND unidade_origem=? AND ativo",
            (produto_id, origem),
        )
        return cur.rowcount > 0


def unidade_base(produto_id: int) -> str:
    """Unidade base do produto: preferência das conversões ativas; fallback para
    os campos legados do produto."""
    with system_conn() as conn:
        r = conn.execute(
            "SELECT unidade_base FROM unidade_conversao "
            "WHERE produto_id=? AND ativo ORDER BY id LIMIT 1",
            (produto_id,),
        ).fetchone()
        if r:
            return r["unidade_base"]
        p = conn.execute(
            "SELECT unidade_venda, unidade_tributavel FROM produtos_cadastro WHERE id=?",
            (produto_id,),
        ).fetchone()
        if p:
            return (p["unidade_tributavel"] or p["unidade_venda"] or "UN")
        return "UN"


def _fator_para_base(produto_id: int, unidade: str, base: str) -> Decimal:
    """Quantas unidades-base equivalem a 1 unidade (conversão direta ou via cadeia)."""
    unidade = (unidade or "").strip().upper() or "UN"
    base = (base or "").strip().upper() or "UN"
    if unidade == base:
        return Decimal("1")
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT unidade_origem, unidade_destino, fator FROM unidade_conversao "
            "WHERE produto_id=? AND ativo",
            (produto_id,),
        ).fetchall()
        conv = [dict(r) for r in rows]
    # direto: unidade -> base
    for c in conv:
        if c["unidade_origem"] == unidade and c["unidade_destino"] == base:
            return Decimal(str(c["fator"]))
    # inverso: base -> unidade (então 1 unidade = 1/fator base)
    for c in conv:
        if c["unidade_origem"] == base and c["unidade_destino"] == unidade:
            f = Decimal(str(c["fator"]))
            return Decimal("1") / f if f else Decimal("1")
    # cadeia: unidade -> X -> base
    for c in conv:
        if c["unidade_origem"] == unidade:
            para_base = _fator_para_base_cadeia(conv, c["unidade_destino"], base)
            if para_base is not None:
                return Decimal(str(c["fator"])) * para_base
    return Decimal("1")


def _fator_para_base_cadeia(conv: list[dict], unidade: str, base: str) -> Decimal | None:
    for c in conv:
        if c["unidade_origem"] == unidade and c["unidade_destino"] == base:
            return Decimal(str(c["fator"]))
    return None


def converter(produto_id: int, quantidade: float, de: str, para: str) -> dict:
    """Converte `quantidade` de `de` para `para`. Retorna o fator aplicado e a
    unidade base usada. Quando não há conversão configurada, usa o fator 1
    (compat com o comportamento atual de `unidade_venda`)."""
    try:
        qtd = Decimal(str(quantidade))
    except (TypeError, ValueError):
        raise ValueError("quantidade inválida") from None
    base = unidade_base(produto_id)
    f_de = _fator_para_base(produto_id, de, base)
    f_para = _fator_para_base(produto_id, para, base)
    fator = f_de / f_para if f_para else Decimal("1")
    return {
        "produto_id": produto_id,
        "de": (de or "").strip().upper() or "UN",
        "para": (para or "").strip().upper() or "UN",
        "quantidade": qtd,
        "fator": fator,
        "resultado": qtd * fator,
        "unidade_base": base,
    }