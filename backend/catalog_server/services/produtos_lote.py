"""Edicao administrativa e transacional de produtos em lote."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from catalog_server.db import system_conn
from catalog_server.repositories import marcas
from catalog_server.services import cadastro_importacao, infra

LIMITE_LOTE = 200
UNIDADES_VALIDAS = {"UN", "CX", "MT", "M", "KG", "G", "LT", "L", "PC", "PCT", "RL", "JG"}


class LoteErro(ValueError):
    def __init__(self, mensagem: str, codigo: str = "lote_invalido", status: int = 400):
        super().__init__(mensagem)
        self.codigo = codigo
        self.status = status


def _id_opcional(valor, campo: str) -> int | None:
    if valor in (None, ""):
        return None
    try:
        convertido = int(valor)
    except (TypeError, ValueError) as exc:
        raise LoteErro(f"{campo} invalido") from exc
    if convertido <= 0:
        raise LoteErro(f"{campo} invalido")
    return convertido


def _preco(valor) -> Decimal:
    try:
        convertido = Decimal(str(valor if valor not in (None, "") else 0))
        if not convertido.is_finite() or convertido < 0:
            raise InvalidOperation
        return convertido.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise LoteErro("preco deve ser um numero maior ou igual a zero") from exc


def _auditavel(item: dict) -> dict:
    return {
        chave: str(valor) if isinstance(valor, Decimal) else valor
        for chave, valor in item.items()
    }


def _carregar_taxonomia(conn):
    grupos = {int(r["id"]): dict(r) for r in conn.execute("SELECT id FROM grupos").fetchall()}
    subgrupos = {
        int(r["id"]): dict(r)
        for r in conn.execute("SELECT id, grupo_id FROM subgrupos").fetchall()
    }
    categorias = {
        int(r["id"]): dict(r)
        for r in conn.execute("SELECT id, subgrupo_id FROM categorias").fetchall()
    }
    subcategorias = {
        int(r["id"]): dict(r)
        for r in conn.execute("SELECT id, categoria_id FROM subcategorias").fetchall()
    }
    return grupos, subgrupos, categorias, subcategorias


def _validar_taxonomia(
    grupo_id: int | None,
    subgrupo_id: int | None,
    categoria_id: int | None,
    subcategoria_id: int | None,
    mapas,
) -> tuple[int | None, int | None, int | None, int | None]:
    grupos, subgrupos, categorias, subcategorias = mapas

    if subcategoria_id is not None:
        subcategoria = subcategorias.get(subcategoria_id)
        if not subcategoria:
            raise LoteErro("subcategoria nao encontrada")
        categoria_da_sub = int(subcategoria["categoria_id"])
        if categoria_id is not None and categoria_id != categoria_da_sub:
            raise LoteErro("subcategoria nao pertence a categoria selecionada")
        categoria_id = categoria_da_sub

    if categoria_id is not None:
        categoria = categorias.get(categoria_id)
        if not categoria:
            raise LoteErro("categoria nao encontrada")
        subgrupo_da_categoria = categoria["subgrupo_id"]
        if subgrupo_da_categoria is not None:
            subgrupo_da_categoria = int(subgrupo_da_categoria)
            if subgrupo_id is not None and subgrupo_id != subgrupo_da_categoria:
                raise LoteErro("categoria nao pertence ao subgrupo selecionado")
            subgrupo_id = subgrupo_da_categoria
    elif subcategoria_id is not None:
        raise LoteErro("selecione uma categoria para a subcategoria")

    if subgrupo_id is not None:
        subgrupo = subgrupos.get(subgrupo_id)
        if not subgrupo:
            raise LoteErro("subgrupo nao encontrado")
        grupo_do_subgrupo = int(subgrupo["grupo_id"])
        if grupo_id is not None and grupo_id != grupo_do_subgrupo:
            raise LoteErro("subgrupo nao pertence ao grupo selecionado")
        grupo_id = grupo_do_subgrupo

    if grupo_id is not None and grupo_id not in grupos:
        raise LoteErro("grupo nao encontrado")

    if categoria_id is None:
        subcategoria_id = None
    return grupo_id, subgrupo_id, categoria_id, subcategoria_id


def atualizar_produtos(itens: list[dict], usuario_id: int | None = None) -> dict:
    if not isinstance(itens, list) or not itens:
        raise LoteErro("informe ao menos um produto")
    if len(itens) > LIMITE_LOTE:
        raise LoteErro(f"o lote permite no maximo {LIMITE_LOTE} produtos")

    ids: list[int] = []
    por_id: dict[int, dict] = {}
    for item in itens:
        if not isinstance(item, dict):
            raise LoteErro("item do lote invalido")
        produto_id = _id_opcional(item.get("id"), "id")
        if produto_id is None:
            raise LoteErro("id do produto e obrigatorio")
        if produto_id in por_id:
            raise LoteErro(f"produto {produto_id} repetido no lote")
        ids.append(produto_id)
        por_id[produto_id] = item

    with system_conn() as conn:
        placeholders = ",".join("?" for _ in ids)
        atuais = conn.execute(
            "SELECT id, nome, marca, preco, unidade_venda, grupo_id, subgrupo_id,"
            " categoria_id, subcategoria_id, status_cadastro, ativo,"
            " COALESCE(atualizado_em, '') AS versao_edicao"
            f" FROM produtos_cadastro WHERE id IN ({placeholders}) ORDER BY id FOR UPDATE",
            tuple(sorted(ids)),
        ).fetchall()
        atual_por_id = {int(r["id"]): dict(r) for r in atuais}
        faltantes = sorted(set(ids) - set(atual_por_id))
        if faltantes:
            raise LoteErro(
                f"produto nao encontrado: {faltantes[0]}", "produto_nao_encontrado", 404
            )

        mapas = _carregar_taxonomia(conn)
        preparados: list[dict] = []
        antes: list[dict] = []
        for produto_id in ids:
            item = por_id[produto_id]
            atual = atual_por_id[produto_id]
            versao = str(item.get("versao_edicao", ""))
            if versao != str(atual["versao_edicao"] or ""):
                raise LoteErro(
                    f"produto {produto_id} foi alterado por outro usuario; recarregue a grade",
                    "edicao_concorrente",
                    409,
                )

            nome = str(item.get("nome", atual["nome"]) or "").strip()
            marca = str(item.get("marca", atual["marca"]) or "").strip()
            unidade = str(item.get("unidade_venda", atual["unidade_venda"] or "UN") or "UN").strip().upper()
            status = str(item.get("status_cadastro", atual["status_cadastro"] or "publicado")).strip().lower()
            if not nome:
                raise LoteErro(f"produto {produto_id}: nome e obrigatorio")
            if len(nome) > 250:
                raise LoteErro(f"produto {produto_id}: nome excede 250 caracteres")
            if len(marca) > 120:
                raise LoteErro(f"produto {produto_id}: marca excede 120 caracteres")
            if unidade not in UNIDADES_VALIDAS:
                raise LoteErro(f"produto {produto_id}: unidade de venda invalida")
            try:
                cadastro_importacao.validar_transicao_status(atual["status_cadastro"], status)
            except ValueError as exc:
                raise LoteErro(f"produto {produto_id}: {exc}") from exc

            grupo_id, subgrupo_id, categoria_id, subcategoria_id = _validar_taxonomia(
                _id_opcional(item.get("grupo_id", atual["grupo_id"]), "grupo_id"),
                _id_opcional(item.get("subgrupo_id", atual["subgrupo_id"]), "subgrupo_id"),
                _id_opcional(item.get("categoria_id", atual["categoria_id"]), "categoria_id"),
                _id_opcional(item.get("subcategoria_id", atual["subcategoria_id"]), "subcategoria_id"),
                mapas,
            )
            preparado = {
                "id": produto_id,
                "nome": nome,
                "marca": marca,
                "preco": _preco(item.get("preco", atual["preco"])),
                "unidade_venda": unidade,
                "grupo_id": grupo_id,
                "subgrupo_id": subgrupo_id,
                "categoria_id": categoria_id,
                "subcategoria_id": subcategoria_id,
                "status_cadastro": status,
                "ativo": cadastro_importacao.ativo_para_status(status),
            }
            preparados.append(preparado)
            antes.append(_auditavel({k: atual.get(k) for k in preparado if k != "id"} | {"id": produto_id}))

        for item in preparados:
            marca_id = marcas.resolver(conn, item["marca"])
            conn.execute(
                "UPDATE produtos_cadastro SET nome=?, marca=?, marca_id=?, preco=?,"
                " unidade_venda=?, grupo_id=?, subgrupo_id=?, categoria_id=?,"
                " subcategoria_id=?, status_cadastro=?, ativo=?,"
                " atualizado_em=to_char(clock_timestamp(),'YYYY-MM-DD HH24:MI:SS.US') WHERE id=?",
                (
                    item["nome"], item["marca"], marca_id, item["preco"],
                    item["unidade_venda"], item["grupo_id"], item["subgrupo_id"],
                    item["categoria_id"], item["subcategoria_id"],
                    item["status_cadastro"], item["ativo"], item["id"],
                ),
            )

        infra.registrar(
            "produtos.edicao_lote",
            alvo_tipo="produto",
            alvo_id=",".join(str(i) for i in ids),
            antes={"produtos": antes},
            depois={"produtos": [_auditavel(item) for item in preparados]},
            motivo=f"Edicao rapida de {len(ids)} produto(s)",
            ator_id=usuario_id,
            conn=conn,
        )
        return {"ok": True, "atualizados": len(preparados), "ids": ids}
