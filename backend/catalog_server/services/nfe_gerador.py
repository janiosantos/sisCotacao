"""Gerador de NF-e/NFC-e (modelo 55/65) — FASE 9.

Gera o XML da nota a partir de um orçamento FATURADO e dos SNAPSHOTS fiscais
(`orcamento_itens_fiscal`). Estrutura segue o layout NF-e 4.00
(ide, emit, dest, det/imposto, total, transp, pag, infAdic).

ATENÇÃO: base ESTRUTURAL — validação XSD e homologação SEFAZ obrigatórias
antes de produção. Campos sem fonte no cadastro (código IBGE do município,
documento/endereço do destinatário não registrado) entram com marcador e
exigem revisão.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from catalog_server.db import system_conn

CUF = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}


def _dv_chave(base: str) -> int:
    pesos = (list(range(2, 10)) * 6)[:43]
    soma = sum(int(d) * pesos[i] for i, d in enumerate(reversed(base)))
    resto = soma % 11
    return 0 if resto in (0, 1) else 11 - resto


def _num(value: float) -> str:
    return f"{float(value):.2f}".replace(".", ",")


def gerar_chave(cuf: str, cnpj: str, modelo: str, serie: int, numero: int, tp_emis: int, cnf: str) -> str:
    aamm = "0000"  # simplificação determinística (usar dhEmi na emissão real)
    base = f"{cuf}{aamm}{cnpj}{modelo}{serie:03d}{numero:09d}{tp_emis}{cnf}"
    return base + str(_dv_chave(base))


def gerar_nfe(orcamento_id: int, c_municipio_emit: str = "", c_municipio_dest: str = "",
              numero: int | None = None, serie: int | None = None) -> dict | None:
    with system_conn() as conn:
        orc = conn.execute("SELECT * FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone()
        if orc is None:
            return None
        orc = dict(orc)
        emit = conn.execute("SELECT * FROM emitente WHERE ativo=1 LIMIT 1").fetchone()
        emit = dict(emit) if emit else {}
        itens_orc = [dict(r) for r in conn.execute(
            "SELECT * FROM orcamento_itens WHERE orcamento_id=? ORDER BY id", (orcamento_id,)
        ).fetchall()]
        snaps = [dict(r) for r in conn.execute(
            "SELECT * FROM orcamento_itens_fiscal WHERE orcamento_id=? ORDER BY item_id", (orcamento_id,)
        ).fetchall()]
        cli = None
        if orc.get("cliente_id"):
            cli_row = conn.execute(
                "SELECT endereco, cidade, uf, cep, c_municipio FROM clientes WHERE id=?",
                (orc["cliente_id"],),
            ).fetchone()
            cli = dict(cli_row) if cli_row else None

    if not emit:
        return {"erro": "Emitente não configurado"}
    if not snaps:
        return {"erro": "Orçamento sem snapshot fiscal (finalize antes de emitir)"}

    modelo = str(orc.get("modelo_documento") or "65")
    serie = serie if serie is not None else int(emit.get("serie_nfe") or 1)
    numero = numero if numero is not None else int(emit.get("proximo_numero_nfe") or 1)
    uf_emit = (emit.get("uf") or "").upper()
    cuf = CUF.get(uf_emit, "99")
    cnf = f"{numero % 100000000:08d}"
    tp_amb = 2 if (emit.get("ambiente_focus") or "homologacao") == "homologacao" else 1
    chave = gerar_chave(cuf, emit.get("cnpj") or "", modelo, serie, numero, 1, cnf)
    c_mun_emit = c_municipio_emit or emit.get("c_municipio") or "0000000"
    c_mun_dest = c_municipio_dest or "0000000"

    snap_por_item = {s["item_id"]: s for s in snaps}

    ns = "http://www.portalfiscal.inf.br/nfe"
    ET.register_namespace("", ns)
    nfe = ET.Element("nfe", {"xmlns": ns})
    inf = ET.SubElement(nfe, "infNFe", {"Id": "NFe" + chave, "versao": "4.00"})

    ide = ET.SubElement(inf, "ide")
    for tag, val in (
        ("cUF", cuf), ("cNF", cnf), ("natOp", "VENDA"), ("mod", modelo), ("serie", str(serie)),
        ("nNF", str(numero)), ("dhEmi", (orc.get("criado_em") or "2026-01-01 00:00:00").replace(" ", "T")),
        ("tpNF", "1"), ("idDest", "1" if (orc.get("uf_destino") or "").upper() == uf_emit else "2"),
        ("cMunFG", c_mun_emit), ("tpImp", "1"), ("tpEmis", "1"), ("cDV", chave[43]),
        ("tpAmb", str(tp_amb)), ("finNFe", "1"), ("indFinal", "1"), ("indPres", "1"),
    ):
        ET.SubElement(ide, tag).text = val

    em = ET.SubElement(inf, "emit")
    ET.SubElement(em, "CNPJ").text = (emit.get("cnpj") or "").strip()
    ET.SubElement(em, "xNome").text = (emit.get("razao_social") or "Emitente").strip()
    if emit.get("nome_fantasia"):
        ET.SubElement(em, "xFant").text = str(emit["nome_fantasia"])
    ET.SubElement(em, "IE").text = (emit.get("ie") or "").strip()
    if emit.get("im"):
        ET.SubElement(em, "IM").text = str(emit["im"])
    ET.SubElement(em, "CRT").text = str(emit.get("crt") or 1)
    ende = ET.SubElement(em, "enderEmit")
    for tag, val in (("xLgr", emit.get("logradouro") or "—"), ("nro", emit.get("numero") or "0"),
                     ("xBairro", emit.get("bairro") or "—"), ("cMun", c_mun_emit),
                     ("xMun", emit.get("municipio") or "—"), ("UF", uf_emit or "MG")):
        ET.SubElement(ende, tag).text = str(val)
    if emit.get("cep"):
        ET.SubElement(ende, "CEP").text = str(emit["cep"])

    dest = ET.SubElement(inf, "dest")
    doc = (orc.get("cliente_doc") or "").strip()
    if len(doc) == 14:
        ET.SubElement(dest, "CNPJ").text = doc
    else:
        ET.SubElement(dest, "CPF").text = (doc or "00000000000")
    ET.SubElement(dest, "xNome").text = (orc.get("cliente") or "CONSUMIDOR FINAL").strip()
    if orc.get("contribuinte") == "contribuinte":
        ind_ie = "1"
        if orc.get("ie"):
            ET.SubElement(dest, "IE").text = str(orc["ie"])
    elif orc.get("ie"):
        ind_ie = "2"
        ET.SubElement(dest, "IE").text = str(orc["ie"])
    else:
        ind_ie = "9"
    ET.SubElement(dest, "indIEDest").text = ind_ie
    if cli and (cli.get("endereco") or cli.get("cidade")):
        ende_d = ET.SubElement(dest, "enderDest")
        for tag, val in (("xLgr", cli.get("endereco") or "—"), ("nro", "S/N"),
                         ("xBairro", "—"), ("cMun", cli.get("c_municipio") or c_mun_dest),
                         ("xMun", cli.get("cidade") or "—"),
                         ("UF", (cli.get("uf") or orc.get("uf_destino") or uf_emit).upper())):
            ET.SubElement(ende_d, tag).text = str(val)
        if cli.get("cep"):
            ET.SubElement(ende_d, "CEP").text = str(cli["cep"])

    v_prod = 0.0
    for i, it in enumerate(itens_orc, start=1):
        snap = snap_por_item.get(it["id"]) or {}
        qtd = float(it.get("quantidade") or 1)
        vun = float(it.get("preco_unitario") or 0)
        vprod = round(qtd * vun, 2)
        v_prod += vprod
        det = ET.SubElement(inf, "det", {"nItem": str(i)})
        prod = ET.SubElement(det, "prod")
        for tag, val in (
            ("cProd", str(snap.get("produto_id") or it.get("produto_id") or f"ITEM{i}")),
            ("cEAN", "SEM GTIN"),
            ("xProd", (it.get("nome") or "Item").strip()),
            ("NCM", snap.get("ncm") or "00000000"),
            ("CFOP", snap.get("cfop") or ""),
            ("uCom", "UN"), ("qCom", _num(qtd)), ("vUnCom", _num(vun)), ("vProd", _num(vprod)),
            ("cEANTrib", "SEM GTIN"), ("uTrib", "UN"), ("qTrib", _num(qtd)),
            ("vUnTrib", _num(vun)), ("indTot", "1"),
        ):
            ET.SubElement(prod, tag).text = val
        if snap.get("cest"):
            ET.SubElement(prod, "CEST").text = str(snap["cest"])
        imp = ET.SubElement(det, "imposto")
        icms = ET.SubElement(imp, "ICMS")
        if snap.get("csosn"):
            g = ET.SubElement(icms, "CSOSN102")
            ET.SubElement(g, "orig").text = str(snap.get("origem") or 0)
            ET.SubElement(g, "CSOSN").text = str(snap["csosn"])
        else:
            g = ET.SubElement(icms, "ICMS00")
            ET.SubElement(g, "orig").text = str(snap.get("origem") or 0)
            ET.SubElement(g, "CST").text = str(snap.get("cst_icms") or "00")
            ET.SubElement(g, "modBC").text = "3"
            ET.SubElement(g, "vBC").text = _num(snap.get("base_icms") or 0)
            ET.SubElement(g, "pICMS").text = _num(snap.get("aliquota_icms") or 0)
            ET.SubElement(g, "vICMS").text = _num(snap.get("valor_icms") or 0)
        pis = ET.SubElement(imp, "PIS")
        cst_pis = str(snap.get("cst_pis") or "07")
        if cst_pis in ("01", "02", "03"):
            g = ET.SubElement(pis, "PISAliq")
            ET.SubElement(g, "CST").text = cst_pis
            ET.SubElement(g, "vBC").text = _num(snap.get("base_icms") or 0)
            ET.SubElement(g, "pPIS").text = _num(snap.get("aliquota_pis") or 0)
            ET.SubElement(g, "vPIS").text = _num(snap.get("valor_pis") or 0)
        else:
            g = ET.SubElement(pis, "PISNT")
            ET.SubElement(g, "CST").text = cst_pis
        cofins = ET.SubElement(imp, "COFINS")
        cst_cofins = str(snap.get("cst_cofins") or "07")
        if cst_cofins in ("01", "02", "03"):
            g = ET.SubElement(cofins, "COFINSAliq")
            ET.SubElement(g, "CST").text = cst_cofins
            ET.SubElement(g, "vBC").text = _num(snap.get("base_icms") or 0)
            ET.SubElement(g, "pCOFINS").text = _num(snap.get("aliquota_cofins") or 0)
            ET.SubElement(g, "vCOFINS").text = _num(snap.get("valor_cofins") or 0)
        else:
            g = ET.SubElement(cofins, "COFINSNT")
            ET.SubElement(g, "CST").text = cst_cofins

    vnf = round(float(orc.get("total") or v_prod), 2)
    total = ET.SubElement(inf, "total")
    t = ET.SubElement(total, "ICMSTot")
    for tag, val in (
        ("vBC", "0,00"), ("vICMS", "0,00"), ("vICMSDeson", "0,00"), ("vFCP", "0,00"),
        ("vBCST", "0,00"), ("vST", "0,00"), ("vProd", _num(v_prod)), ("vFrete", "0,00"),
        ("vSeg", "0,00"), ("vDesc", _num(orc.get("desconto") or 0)), ("vII", "0,00"),
        ("vIPI", "0,00"), ("vIPIDevol", "0,00"), ("vPIS", "0,00"), ("vCOFINS", "0,00"),
        ("vOutro", "0,00"), ("vNF", _num(vnf)),
    ):
        ET.SubElement(t, tag).text = val
    transp = ET.SubElement(inf, "transp")
    ET.SubElement(transp, "modFrete").text = "9"
    pag = ET.SubElement(inf, "pag")
    dp = ET.SubElement(pag, "detPag")
    ET.SubElement(dp, "tPag").text = "01"
    ET.SubElement(dp, "vPag").text = _num(vnf)
    inf_ad = ET.SubElement(inf, "infAdic")
    ET.SubElement(inf_ad, "infCpl").text = "Documento gerado pelo sistema de cotações. Regras fiscais sujeitas a validação."

    ET.indent(nfe, space="  ")
    xml = ET.tostring(nfe, encoding="unicode")

    return {
        "xml": xml,
        "numero": numero,
        "serie": serie,
        "chave": chave,
        "modelo": modelo,
        "uf_origem": uf_emit,
        "ambiente": "homologacao" if tp_amb == 2 else "producao",
    }
