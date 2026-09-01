"""Entrada fiscal XML (REC-004): importa XML da NF-e, valida chave única,
extrai fornecedor/itens, faz matching (código fornecedor/EAN/descrição) e
permite vínculo manual antes da confirmação.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from catalog_server.db import system_conn
from catalog_server.services import produto_identificador

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def _tag(elem, name: str) -> str | None:
    el = elem.find(f"nfe:{name}", NS)
    return el.text.strip() if el is not None and el.text else None


def importar_xml(xml_conteudo: str) -> dict:
    xml_conteudo = (xml_conteudo or "").strip()
    if not xml_conteudo:
        raise ValueError("XML vazio")
    try:
        root = ET.fromstring(xml_conteudo)
    except ET.ParseError as exc:
        raise ValueError(f"XML inválido: {exc}") from None

    nfe = root if root.tag.endswith("}NFe") or root.tag == "NFe" else root.find(".//nfe:NFe", NS)
    if nfe is None:
        raise ValueError("Estrutura de NF-e não encontrada")
    inf = nfe.find("nfe:infNFe", NS)
    if inf is None:
        raise ValueError("infNFe não encontrado")

    # assinatura/validação simplificada: presença de chave + protocolo
    chave = inf.get("Id", "")
    chave = chave[3:] if chave.startswith("NFe") else chave
    if len(chave) != 44:
        raise ValueError("Chave de acesso inválida")

    ide = inf.find("nfe:ide", NS)
    emit = inf.find("nfe:emit", NS)
    numero = _tag(ide, "nNF") if ide is not None else None
    serie = _tag(ide, "serie") if ide is not None else None
    dh_emi = _tag(ide, "dhEmi") if ide is not None else None
    cnpj = _tag(emit, "CNPJ") if emit is not None else None

    fornecedor_id = None
    fornecedor_nome = ""
    fornecedor_doc = cnpj or ""
    if cnpj:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT id, nome, cnpj_cpf FROM fornecedores WHERE cnpj_cpf=?", (cnpj,)
            ).fetchone()
            if row:
                fornecedor_id = row["id"]
                fornecedor_nome = row["nome"] or ""
                fornecedor_doc = row["cnpj_cpf"] or cnpj

    itens_extraidos = []
    total = 0.0
    for det in inf.findall("nfe:det", NS):
        prod = det.find("nfe:prod", NS)
        if prod is None:
            continue
        cod = _tag(prod, "cProd")
        ean = _tag(prod, "cEAN") or ""
        desc = _tag(prod, "xProd")
        ncm = _tag(prod, "NCM")
        cfop = _tag(prod, "CFOP")
        ucom = _tag(prod, "uCom")
        try:
            qcom = float(_tag(prod, "qCom") or 0)
            vun = float(_tag(prod, "vUnCom") or 0)
        except ValueError:
            qcom = vun = 0.0
        cst = None
        imposto = det.find("nfe:imposto", NS)
        if imposto is not None:
            cst_el = imposto.find(".//nfe:CST", NS)
            cst = cst_el.text if cst_el is not None and cst_el.text else None
        total += qcom * vun
        itens_extraidos.append({
            "codigo_fornecedor": cod, "ean": ean, "descricao": desc, "ncm": ncm,
            "cfop": cfop, "cst": cst, "unidade": ucom, "quantidade": qcom,
            "valor_unitario": round(vun, 4),
        })

    with system_conn() as conn:
        duplicado = conn.execute(
            "SELECT id FROM nfe_entrada WHERE chave_acesso=?", (chave,)
        ).fetchone()
        if duplicado:
            raise ValueError("XML duplicado: chave já importada")

        nfe_id = conn.execute(
            "INSERT INTO nfe_entrada (chave, chave_acesso, numero, serie, fornecedor_id, fornecedor_nome,"
            " fornecedor_doc, emissao, valor, valor_total, data_emissao, xml, status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'importado') RETURNING id",
            (chave, chave, numero, serie, fornecedor_id, fornecedor_nome, fornecedor_doc,
             (dh_emi or "")[:10], round(total, 2), round(total, 2), (dh_emi or "")[:10], xml_conteudo),
        ).fetchone()["id"]

        for it in itens_extraidos:
            produto_id = _match_produto(conn, it)
            conn.execute(
                "INSERT INTO nfe_entrada_item (nfe_id, produto_id, codigo_fornecedor, ean, descricao,"
                " ncm, cfop, cst, unidade, quantidade, valor_unitario, status)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (nfe_id, produto_id, it["codigo_fornecedor"], it["ean"], it["descricao"],
                 it["ncm"], it["cfop"], it["cst"], it["unidade"], it["quantidade"],
                 it["valor_unitario"], "vinculado" if produto_id else "sem_vinculo"),
            )
        vinculados = sum(1 for it in itens_extraidos if _match_produto(conn, it))
        if vinculados == len(itens_extraidos) and len(itens_extraidos) > 0:
            conn.execute("UPDATE nfe_entrada SET status='vinculado' WHERE id=?", (nfe_id,))

    return {"id": nfe_id, "chave_acesso": chave, "fornecedor_id": fornecedor_id,
            "itens": len(itens_extraidos), "vinculados": vinculados}


def _match_produto(conn, item: dict) -> int | None:
    """Matching por código fornecedor → EAN → descrição (com confirmação humana depois)."""
    if item.get("codigo_fornecedor"):
        encontrados = produto_identificador.buscar(item["codigo_fornecedor"], limite=1)
        if encontrados:
            return encontrados[0]["id"]
    if item.get("ean") and len(item["ean"].strip()) >= 8:
        row = conn.execute(
            "SELECT id FROM produtos_cadastro WHERE ean=? LIMIT 1", (item["ean"].strip(),)
        ).fetchone()
        if row:
            return row["id"]
    if item.get("descricao"):
        row = conn.execute(
            "SELECT id FROM produtos_cadastro WHERE LOWER(nome)=LOWER(?) LIMIT 1",
            (item["descricao"].strip(),),
        ).fetchone()
        if row:
            return row["id"]
    return None


def vincular_item(nfe_item_id: int, produto_id: int) -> dict:
    with system_conn() as conn:
        item = conn.execute("SELECT * FROM nfe_entrada_item WHERE id=?", (nfe_item_id,)).fetchone()
        if not item:
            raise LookupError("Item da NF não encontrado")
        conn.execute(
            "UPDATE nfe_entrada_item SET produto_id=?, status='vinculado' WHERE id=?",
            (produto_id, nfe_item_id),
        )
        sem = conn.execute(
            "SELECT COUNT(*) FROM nfe_entrada_item WHERE nfe_id=? AND status='sem_vinculo'",
            (item["nfe_id"],),
        ).fetchone()["count"]
        if sem == 0:
            conn.execute("UPDATE nfe_entrada SET status='vinculado' WHERE id=?", (item["nfe_id"],))
    return {"item_id": nfe_item_id, "produto_id": produto_id}


def confirmar(nfe_id: int) -> dict:
    """Confirma a NF: devolve linhas normalizadas (itens vinculados) p/ a conferência de três vias."""
    with system_conn() as conn:
        nfe = conn.execute("SELECT * FROM nfe_entrada WHERE id=?", (nfe_id,)).fetchone()
        if not nfe:
            raise LookupError("NF não encontrada")
        if nfe["status"] == "rejeitado":
            raise ValueError("NF rejeitada não pode ser confirmada")
        itens = [dict(r) for r in conn.execute(
            "SELECT * FROM nfe_entrada_item WHERE nfe_id=? ORDER BY id", (nfe_id,)
        ).fetchall()]
        sem = [i for i in itens if not i["produto_id"]]
        if sem:
            raise ValueError(f"Existem {len(sem)} item(ns) sem vínculo de produto — vincule antes de confirmar")
        linhas = [{"produto_id": i["produto_id"], "quantidade": i["quantidade"],
                   "preco_unitario": i["valor_unitario"]} for i in itens]
        conn.execute("UPDATE nfe_entrada SET status='confirmado' WHERE id=?", (nfe_id,))
    return {"nfe_id": nfe_id, "itens_nf": linhas}


def rejeitar(nfe_id: int, motivo: str) -> dict:
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("motivo é obrigatório")
    with system_conn() as conn:
        cur = conn.execute("UPDATE nfe_entrada SET status='rejeitado' WHERE id=?", (nfe_id,))
        if cur.rowcount == 0:
            raise LookupError("NF não encontrada")
    return {"nfe_id": nfe_id, "status": "rejeitado"}


def listar(status: str | None = None) -> list[dict]:
    sql = (
        "SELECT n.*, f.nome AS fornecedor_nome,"
        " (SELECT COUNT(*) FROM nfe_entrada_item i WHERE i.nfe_id=n.id) AS itens"
        " FROM nfe_entrada n LEFT JOIN fornecedores f ON f.id=n.fornecedor_id"
    )
    args: list = []
    if status:
        sql += " WHERE n.status=?"
        args.append(status)
    sql += " ORDER BY n.id DESC"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def detalhe(nfe_id: int) -> dict | None:
    with system_conn() as conn:
        nfe = conn.execute(
            "SELECT n.*, f.nome AS fornecedor_nome FROM nfe_entrada n"
            " LEFT JOIN fornecedores f ON f.id=n.fornecedor_id WHERE n.id=?",
            (nfe_id,),
        ).fetchone()
        if not nfe:
            return None
        itens = [dict(r) for r in conn.execute(
            "SELECT i.*, p.sku, p.nome AS produto_nome FROM nfe_entrada_item i"
            " LEFT JOIN produtos_cadastro p ON p.id=i.produto_id WHERE i.nfe_id=? ORDER BY i.id",
            (nfe_id,),
        ).fetchall()]
        out = dict(nfe)
        out["itens"] = itens
        return out