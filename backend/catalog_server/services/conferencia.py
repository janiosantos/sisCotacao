"""Conferência por código/unidade (REC-002): resolução de identificador
(EAN/código interno/SKU), conversão para unidade base e divergência. Produto
desconhecido vai para exceção; caixa/rolo não gera quantidade errada.
"""

from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import produto_identificador, unidade_conversao
from catalog_server.services import recebimento as recebimento_svc


def resolver_codigo(codigo: str) -> dict | None:
    """Resolve código (EAN/código interno/SKU) para produto + unidade/fator."""
    codigo = (codigo or "").strip()
    if not codigo:
        return None
    with system_conn() as conn:
        # 1) identificadores múltiplos (MDM-003) — busca exata antes de textual
        encontrados = produto_identificador.buscar(codigo, limite=1)
        if encontrados:
            return _montar(conn, encontrados[0]["id"], None)
        # 2) SKU/EAN do produto
        row = conn.execute(
            "SELECT id FROM produtos_cadastro WHERE sku=? OR ean=? LIMIT 1",
            (codigo, codigo),
        ).fetchone()
        if row:
            return _montar(conn, row["id"], None)
        # 3) código fornecedor (identificador tipo 'codigo_fornecedor')
        row = conn.execute(
            "SELECT i.produto_id FROM produto_identificador i WHERE i.valor=? LIMIT 1",
            (codigo,),
        ).fetchone()
        if row:
            return _montar(conn, row["produto_id"], None)
    return None


def _montar(conn, produto_id: int, ident) -> dict:
    p = conn.execute(
        "SELECT id, nome, sku, ean, unidade_venda, fator_conversao FROM produtos_cadastro WHERE id=?",
        (produto_id,),
    ).fetchone()
    if not p:
        return None
    base = unidade_conversao.unidade_base(produto_id)
    return {
        "produto_id": p["id"], "sku": p["sku"], "nome": p["nome"], "ean": p["ean"],
        "unidade_base": base,
        "unidade_venda": p["unidade_venda"] or "UN",
        "fator_conversao": float(p["fator_conversao"] or 1),
    }


def converter_para_base(produto_id: int, quantidade: float, unidade: str) -> float:
    """Converte quantidade na unidade conferida para a unidade base."""
    base = unidade_conversao.unidade_base(produto_id)
    unidade = (unidade or base).strip().upper()
    if unidade == base:
        return float(quantidade)
    try:
        r = unidade_conversao.converter(produto_id, float(quantidade), unidade, base)
        return float(r.get("resultado") or 0)
    except Exception:  # noqa: BLE001 (sem conversão → assume 1:1 e marca exceção)
        return float(quantidade)


def conferir_por_codigo(recebimento_id: int, codigo: str, quantidade: float, unidade: str | None = None,
                        operador_id: int | None = None) -> dict:
    """Conferência por scanner: resolve código, converte e confere o item."""
    resolvido = resolver_codigo(codigo)
    if not resolvido:
        raise ValueError(f"Produto desconhecido: {codigo}")
    produto_id = resolvido["produto_id"]
    det = recebimento_svc.detalhe(recebimento_id)
    if not det:
        raise LookupError("Recebimento não encontrado")
    item = next((i for i in det["itens"] if i["produto_id"] == produto_id), None)
    if not item:
        raise ValueError(f"Produto {resolvido['nome']} não está na lista de conferência deste recebimento")

    qtd_base = converter_para_base(produto_id, quantidade, unidade or resolvido["unidade_venda"])
    esperado = float(item["qtd_pedido"] or 0)
    resultado = recebimento_svc.conferir_item(
        recebimento_id, item["id"], qtd_base,
    )
    with system_conn() as conn:
        conn.execute(
            "UPDATE recebimento_item SET codigo_conferido=?, unidade_conferida=? WHERE id=?",
            (codigo, (unidade or resolvido["unidade_venda"]).upper(), item["id"]),
        )
    return {
        "produto_id": produto_id,
        "sku": resolvido["sku"], "nome": resolvido["nome"],
        "unidade_base": resolvido["unidade_base"],
        "unidade_conferida": (unidade or resolvido["unidade_venda"]).upper(),
        "quantidade_base": qtd_base,
        "quantidade_esperada": esperado,
        "divergencia": round(qtd_base - esperado, 3),
        "status": resultado.get("status"),
    }