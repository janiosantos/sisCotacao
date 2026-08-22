"""Importador da tabela IBPT (carga tributária por NCM).

Lê o arquivo fornecido pelo IBPT ("De Olho no Imposto" / IBPTax, `.csv` ou
`.csc`) e alimenta a tabela `ibpt` de forma idempotente.

Formato esperado (separador `;`):
    codigo;ex;tipo;descricao;nacionalfederal;importadosfederal;estadual;municipal;
    vigenciainicio;vigenciafim;chave;versao;fonte

Mapeamento para a tabela `ibpt`:
- ncm                = codigo
- descricao          = descricao
- aliquota_federal   = nacionalfederal (alíquota para produto nacional)
- aliquota_estadual  = estadual
- aliquota_municipal = municipal
- fonte / vigência   = fonte, vigenciainicio, vigenciafim (dd/mm/aaaa → aaaa-mm-dd)

Uso:
    python -m catalog_server.importar_ibpt [--arquivo CAMINHO] [--limite N]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from catalog_server.db import system_conn

DEFAULT_ARQUIVO = (
    Path(__file__).resolve().parents[1] / "documentacao_ibpt" / "TabelaIBPTaxMG26.1.L.csv"
)

COLUNAS = {
    "codigo", "ex", "tipo", "descricao", "nacionalfederal", "importadosfederal",
    "estadual", "municipal", "vigenciainicio", "vigenciafim", "chave", "versao", "fonte",
}


def _data(v: str | None) -> str | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        d, m, a = v.split("/")
        return f"{a.strip()}-{m.strip()}-{d.strip()}"
    except ValueError:
        return None


def importar(arquivo: Path, limite: int | None = None) -> dict:
    linhas = []
    vistos: set[str] = set()
    ignorados = 0
    with open(arquivo, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not reader.fieldnames or not COLUNAS.issubset(set(reader.fieldnames)):
            raise ValueError(
                "Formato inesperado. Colunas esperadas (IBPT): " + ";".join(sorted(COLUNAS))
            )
        for row in reader:
            ncm = (row.get("codigo") or "").strip()
            if len(ncm) != 8 or not ncm.isdigit() or ncm in vistos:
                ignorados += 1
                continue
            vistos.add(ncm)
            linhas.append((
                ncm,
                (row.get("descricao") or "").strip(),
                float((row.get("nacionalfederal") or 0).replace(",", ".")),
                float((row.get("estadual") or 0).replace(",", ".")),
                float((row.get("municipal") or 0).replace(",", ".")),
                (row.get("fonte") or "").strip(),
                _data(row.get("vigenciainicio")),
                _data(row.get("vigenciafim")),
            ))
            if limite and len(linhas) >= limite:
                break

    if linhas:
        with system_conn() as conn:
            conn.executemany(
                "INSERT INTO ibpt (ncm, descricao, aliquota_federal, aliquota_estadual, aliquota_municipal,"
                " fonte, vigencia_inicio, vigencia_fim)"
                " VALUES (?,?,?,?,?,?,?,?)"
                " ON CONFLICT(ncm) DO UPDATE SET"
                " descricao=excluded.descricao, aliquota_federal=excluded.aliquota_federal,"
                " aliquota_estadual=excluded.aliquota_estadual, aliquota_municipal=excluded.aliquota_municipal,"
                " fonte=excluded.fonte, vigencia_inicio=excluded.vigencia_inicio, vigencia_fim=excluded.vigencia_fim",
                linhas,
            )
    return {"importados": len(linhas), "ignorados": ignorados, "arquivo": str(arquivo)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Importa a tabela IBPT para o banco")
    ap.add_argument("--arquivo", default=str(DEFAULT_ARQUIVO))
    ap.add_argument("--limite", type=int, default=None, help="importa só N linhas (teste)")
    args = ap.parse_args()
    resultado = importar(Path(args.arquivo), limite=args.limite)
    print(resultado)
