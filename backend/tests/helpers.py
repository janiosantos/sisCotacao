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


def variante(sku: str, ean: str, atributos: dict, preco: float = 10.0) -> dict:
    return {
        "sku": sku,
        "ean": ean,
        "preco": preco,
        "preco_promocional": None,
        "observacao": "",
        "atributos": atributos,
        "ncm": "",
        "unidade_venda": "MT",
    }