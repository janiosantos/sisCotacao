"""FASE 10 — Suíte de regressão fiscal (FASE 3..9).

Roda todos os cenários-chave do motor fiscal e emite PASS/FAIL. Uso:
    python -m catalog_server.testar_fiscal  (na raiz do projeto)
Retorna 0 se tudo passar.
"""
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.getcwd())

from catalog_server.app_factory import create_app  # noqa: E402
from catalog_server.db import system_conn  # noqa: E402
from catalog_server.repositories import emitente_repo  # noqa: E402
from catalog_server.services import fiscal_motor, nfe_gerador  # noqa: E402

PASS = 0
FAIL = 0


def ok(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {nome} {extra}")
    else:
        FAIL += 1
        print(f"  FAIL {nome} {extra}")


def main() -> int:
    app = create_app()
    client = app.test_client()

    # Garante um emitente ativo isolado (container pode ter emitente inativo/pré-existente)
    with system_conn() as conn:
        conn.execute("DELETE FROM emitente")
    emitente_repo.upsert({"razao_social": "Empresa MG", "cnpj": "00000000000000", "ie": "001234",
                          "uf": "MG", "regime_tributario": "simples_nacional", "crt": 1,
                          "aliquota_icms": 18, "serie_nfe": 1, "proximo_numero_nfe": 1,
                          "municipio": "Belo Horizonte", "logradouro": "Rua A",
                          "bairro": "Centro", "cep": "30100000", "ativo": 1,
                          "aliquota_ibs": 0.1, "aliquota_cbs": 0.9,
                          "ibs_vigencia_inicio": "2026-01-01", "ibs_vigencia_fim": "2026-12-31",
                          "cbs_vigencia_inicio": "2026-01-01", "cbs_vigencia_fim": "2026-12-31"})

    with system_conn() as conn:
        vid_ok = conn.execute("SELECT id FROM produtos_cadastro LIMIT 1").fetchone()["id"]
        conn.execute("DELETE FROM fiscal_config WHERE produto_id=?", (vid_ok,))
        conn.execute("INSERT INTO fiscal_config (produto_id, ncm, cfop, csosn, aliquota_icms) VALUES (?,?,?,?,?)",
                     (vid_ok, "85362000", "5.102", "102", 18))
        vid_st = conn.execute("SELECT id FROM produtos_cadastro WHERE id <> ? LIMIT 1", (vid_ok,)).fetchone()["id"]
        conn.execute("INSERT OR REPLACE INTO fiscal_config (produto_id, ncm, cfop, csosn, aliquota_icms) VALUES (?,?,?,?,?)",
                     (vid_st, "82041100", "5.102", "102", 18))
        vid_sem = conn.execute("SELECT id FROM produtos_cadastro WHERE id NOT IN (?,?) LIMIT 1", (vid_ok, vid_st)).fetchone()["id"]
        conn.execute("INSERT OR REPLACE INTO fiscal_config (produto_id, ncm, cfop, csosn, aliquota_icms) VALUES (?,?,?,?,?)",
                     (vid_sem, "", "5.102", "102", 18))
        conn.execute("UPDATE orcamentos SET modelo_documento='65'")

    ctx = {"operacao": "venda", "uf_destino": "SP", "tipo_cliente": "PJ", "contribuinte": "contribuinte",
           "modelo_documento": "55", "data": "2026-06-01", "quantidade": 1, "valor_unitario": 100}

    print("== FASE 3/4 — motor + composição + validação ==")
    r = fiscal_motor.simular({**ctx, "produto_id": vid_st})
    ok("matriz interestadual CFOP", r["cfop"] == "6.102", r["cfop"])
    ok("CSOSN matriz", r["csosn"] == "102", r["csosn"])
    ok("memoria versao simulada", r["memoria"]["versao"] == "1.0-SIMULADO")
    r = fiscal_motor.simular({**ctx, "produto_id": vid_ok})
    ok("composicao ST+CFOP", r["cfop"] == "6.102" and r["csosn"] == "106", f"{r['cfop']}/{r['csosn']}")
    ok("ICMS-ST valor", abs(r["valor_icms_st"] - 25.20) < 0.01, r["valor_icms_st"])
    r = fiscal_motor.simular({**ctx, "produto_id": 999999999})
    ok("FISCAL_RULE_NOT_FOUND", r["status"] == "FISCAL_RULE_NOT_FOUND")

    print("== FASE 5 — PIS/COFINS ==")
    r = fiscal_motor.simular({**ctx, "uf_destino": "MG", "produto_id": vid_st})
    ok("Simples PIS/COFINS nao destacado", r["valor_pis"] == 0 and r["valor_cofins"] == 0)

    print("== FASE 6 — IBS/CBS ==")
    r = fiscal_motor.simular({**ctx, "produto_id": vid_st, "data": "2026-06-01"})
    ok("IBS 2026", abs(r["valor_ibs"] - 0.10) < 0.01, r["valor_ibs"])
    ok("CBS 2026", abs(r["valor_cbs"] - 0.90) < 0.01, r["valor_cbs"])
    r = fiscal_motor.simular({**ctx, "produto_id": vid_st, "data": "2027-06-01"})
    ok("IBS fora vigencia", r["valor_ibs"] == 0 and r["valor_cbs"] == 0)

    print("== FASE 8 — snapshot + bloqueio na venda ==")
    r = client.post("/api/orcamentos", json={"cliente": "Cli", "itens": [
        {"nome": "Ok", "produto_id": vid_st, "quantidade": 1, "preco_unitario": 100.0}]})
    oid_ok = r.get_json()["id"]
    ok("finaliza com NCM", client.patch(f"/api/orcamentos/{oid_ok}", json={"status": "finalizado"}).status_code == 200)
    r = client.post("/api/orcamentos", json={"cliente": "Cli2", "itens": [
        {"nome": "Sem NCM", "produto_id": vid_sem, "quantidade": 1, "preco_unitario": 50.0}]})
    oid_sem = r.get_json()["id"]
    r = client.patch(f"/api/orcamentos/{oid_sem}", json={"status": "finalizado"})
    ok("bloqueio sem NCM", r.status_code == 403 and r.get_json().get("code") == "fiscal_error")

    print("== FASE 9 — emissão NF-e ==")
    r = client.post(f"/api/nfe/emitir/{oid_ok}", json={"c_municipio_emit": "3106200"})
    ok("emitir 201", r.status_code == 201, r.status_code)
    chave = r.get_json().get("chave", "")
    ok("chave 44", len(chave) == 44)
    with system_conn() as conn:
        row = conn.execute("SELECT xml FROM nfe_saida WHERE orcamento_id=?", (oid_ok,)).fetchone()
    well = False
    if row:
        try:
            root = ET.fromstring(row["xml"])
            tags = {c.tag.split("}")[-1] for c in root.iter()}
            well = {"ide", "emit", "dest", "det", "total"} <= tags
        except ET.ParseError:
            well = False
    ok("XML bem formado + elementos", well)

    print(f"\nRESULTADO: {PASS} PASS · {FAIL} FAIL")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
