"""Serialização de relatórios para arquivos baixáveis.

PDF permanece baseado no template de impressão, pois isso garante que a
visualização e o documento paginado tenham a mesma fonte de dados. CSV e XLSX
são gerados sem depender de bibliotecas opcionais no worker web.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date, datetime
from html import escape
from typing import Iterable

from catalog_server.db import system_conn


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    return str(value)


def _safe_csv(value) -> str:
    text = _text(value)
    if text[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def _audit(actor_id: int | None, report_key: str, formato: str, filtros: dict, rows: int, ip: str | None = None) -> None:
    if not actor_id:
        return
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO auditoria_evento "
            "(ator_id, acao, alvo_tipo, alvo_id, depois, ip, correlation_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (actor_id, "exportar_relatorio", "relatorio", report_key,
             json.dumps({"formato": formato, "filtros": filtros, "linhas": rows}),
             ip, None),
        )
        conn.commit()


def _cliente_rows(data: dict) -> tuple[list[str], Iterable[list[object]]]:
    columns = ["ID", "Nome", "Tipo", "Documento", "E-mail", "Telefone", "Cidade", "UF", "Segmento", "Categoria", "Vendedor", "Nascimento", "Última compra", "Ativo"]
    rows = []
    for item in data.get("itens", []):
        rows.append([
            item.get("id"), item.get("nome"), item.get("tipo_pessoa"), item.get("doc"), item.get("email"),
            item.get("telefone"), item.get("cidade"), item.get("uf"), item.get("segmento"), item.get("categoria"),
            item.get("vendedor_nome"), item.get("data_nascimento"), item.get("ultima_compra"), item.get("ativo"),
        ])
    return columns, rows


def _compra_rows(data: dict) -> tuple[list[str], Iterable[list[object]]]:
    columns = ["Pedido", "Data", "Status", "Produto", "SKU", "Marca", "Quantidade", "Preço unitário", "Desconto %", "Total item", "Vendedor"]
    rows = []
    for item in data.get("itens", []):
        rows.append([
            item.get("numero"), item.get("data_venda"), item.get("status"), item.get("nome"), item.get("sku"),
            item.get("marca"), item.get("quantidade"), item.get("preco_unitario"), item.get("desconto_percentual"),
            item.get("total_item"), item.get("vendedor_nome"),
        ])
    return columns, rows


def rows_for(report_key: str, data: dict) -> tuple[list[str], list[list[object]]]:
    if report_key == "dashboard":
        kpis = data.get("kpis", {})
        columns = ["Indicador", "Valor"]
        rows = [[label, kpis.get(key)] for key, label in (
            ("pedidos", "Pedidos"),
            ("receita_bruta", "Receita bruta"),
            ("desconto", "Descontos"),
            ("receita_liquida", "Receita líquida"),
            ("cmv", "CMV"),
            ("margem_pct", "Margem (%)"),
            ("ticket_medio", "Ticket médio"),
            ("caixa", "Saldo de caixa"),
            ("inadimplencia", "Inadimplência"),
            ("estoque_valorizado", "Estoque valorizado"),
            ("compras_abertas", "Compras em aberto"),
        )]
    elif report_key == "clientes":
        columns, rows = _cliente_rows(data)
    elif report_key == "clientes.compras":
        columns, rows = _compra_rows(data)
    elif report_key == "vendas":
        columns = ["Chave", "Receita bruta", "Receita líquida", "Pedidos"]
        rows = [[item.get("chave"), item.get("receita_bruta"), item.get("receita_liquida"), item.get("pedidos")] for item in data.get("itens", [])]
    elif report_key == "vendas.analitico":
        columns = ["Dimensão", "Quantidade", "Pedidos", "Clientes", "Receita bruta", "Desconto", "Receita líquida", "CMV", "Margem bruta", "Margem %"]
        rows = [[item.get("dimensao"), item.get("quantidade"), item.get("pedidos"), item.get("clientes"), item.get("receita_bruta"), item.get("desconto"), item.get("receita_liquida"), item.get("cmv"), item.get("margem_bruta"), item.get("margem_pct")] for item in data.get("itens", [])]
    elif report_key == "compras":
        columns = ["Indicador", "Valor"]
        rows = [["Pedidos", data.get("pedidos")], ["Recebidos", data.get("recebidos")], ["Cancelados", data.get("cancelados")], ["Lead time médio (dias)", data.get("lead_time_medio_dias")], ["Comprado", data.get("comprado")]]
    elif report_key == "compras.analitico":
        columns = ["Pedido", "Número", "Status", "Data", "Fornecedor", "Produto", "SKU", "Qtd. pedida", "Qtd. recebida", "Qtd. pendente", "Preço", "Valor pedido", "Valor recebido"]
        rows = [[item.get("pedido_id"), item.get("numero"), item.get("status"), item.get("data_pedido"), item.get("fornecedor_nome"), item.get("produto_nome"), item.get("sku"), item.get("quantidade_pedida"), item.get("quantidade_recebida"), item.get("quantidade_pendente"), item.get("preco_unitario"), item.get("valor_pedido"), item.get("valor_recebido")] for item in data.get("itens", [])]
    elif report_key == "estoque":
        columns = ["ID", "SKU", "Produto", "Quantidade", "Disponível", "Valor"]
        rows = [[item.get("id"), item.get("sku"), item.get("nome"), item.get("quantidade"), item.get("disponivel"), item.get("valor")] for item in data.get("itens", [])]
    elif report_key == "estoque.analitico":
        columns = ["Produto", "SKU", "Depósito", "ABC", "XYZ", "Quantidade", "Disponível", "Mínimo", "Máximo", "Custo médio", "Valor", "Situação"]
        rows = [[item.get("nome"), item.get("sku"), item.get("deposito_nome"), item.get("classe_abc"), item.get("classe_xyz"), item.get("quantidade"), item.get("disponivel"), item.get("estoque_minimo"), item.get("estoque_maximo"), item.get("custo_medio"), item.get("valor"), item.get("situacao")] for item in data.get("itens", [])]
    elif report_key == "financeiro":
        columns = ["Grupo", "Indicador", "Valor"]
        rows = [["Fluxo de caixa", "Entradas", data.get("fluxo_caixa", {}).get("entradas")], ["Fluxo de caixa", "Saídas", data.get("fluxo_caixa", {}).get("saidas")], ["Aging", "A vencer", data.get("aging", {}).get("a_vencer")], ["Aging", "Vencido", data.get("aging", {}).get("vencido")], ["DRE", "Receita líquida", data.get("dre", {}).get("receita_liquida")], ["DRE", "CMV", data.get("dre", {}).get("cmv")], ["DRE", "Lucro bruto", data.get("dre", {}).get("lucro_bruto")]]
    else:
        raise ValueError("Relatório não possui exportador")
    return columns, list(rows)


def csv_bytes(report_key: str, data: dict, *, actor_id: int | None = None, filtros: dict | None = None, ip: str | None = None) -> bytes:
    columns, rows = rows_for(report_key, data)
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(columns)
    writer.writerows([[_safe_csv(value) for value in row] for row in rows])
    _audit(actor_id, report_key, "csv", filtros or {}, len(rows), ip)
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def _column_name(number: int) -> str:
    out = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        out = chr(65 + remainder) + out
    return out


def _xlsx_cell(ref: str, value) -> str:
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = escape(_text(value))
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def xlsx_bytes(report_key: str, data: dict, *, actor_id: int | None = None, filtros: dict | None = None, ip: str | None = None) -> bytes:
    columns, rows = rows_for(report_key, data)
    all_rows = [columns, *rows]
    xml_rows = []
    for row_number, row in enumerate(all_rows, 1):
        cells = "".join(_xlsx_cell(f"{_column_name(col_number)}{row_number}", value) for col_number, value in enumerate(row, 1))
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')
    last_ref = f"{_column_name(len(columns))}{len(all_rows)}"
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:{last_ref}"/><sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>')
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Dados" sheetId="1" r:id="rId1"/></sheets></workbook>')
    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>')
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    _audit(actor_id, report_key, "xlsx", filtros or {}, len(rows), ip)
    return output.getvalue()
