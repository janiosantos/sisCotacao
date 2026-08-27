"""Helpers compartilhados para os testes de regressão."""
from __future__ import annotations


def criar_familia(repo, nome="Familia Teste", ncm_padrao="85444900", unidade_padrao="MT"):
    """Cria uma família com dois atributos (Bitola, Cor)."""
    return repo.create_familia(
        nome,
        "descricao",
        [
            {"nome": "Bitola", "tipo": "lista", "opcoes": ["2,5mm", "4mm"]},
            {"nome": "Cor", "tipo": "lista", "opcoes": ["Verde", "Azul"]},
        ],
        ncm_padrao=ncm_padrao,
        unidade_padrao=unidade_padrao,
    )


def attr_ids(repo, familia_id):
    fam = repo.get_familia(familia_id)
    return {a["nome"]: str(a["id"]) for a in fam["atributos"]}


def attrs(attr_ids: dict, **vals: str) -> dict:
    return {attr_ids[k]: v for k, v in vals.items()}


def produto_dados(sku: str, ean: str, preco: float = 10.0, **extra) -> dict:
    """Dados operacionais de um produto (campos de `produtos_cadastro`).

    No modelo unificado cada antiga variação tornou-se um produto próprio,
    então o SKU/EAN/preço que antes viviam numa linha de `variantes` agora
    são passados via `dados=...` ao criar o produto.
    """
    return {"sku": sku, "ean": ean, "preco": preco, **extra}