"""Roundtrip do snapshot fiscal: persistir -> explicar (auditoria §22)."""
from __future__ import annotations

from decimal import Decimal

from catalog_server.db import system_conn
from catalog_server.fiscal import EstadoFiscal, FiscalResult
from catalog_server.fiscal.snapshot import explicar, persistir


def _variante():
    sufixo = uuid_hex()
    with system_conn() as conn:
        vid = conn.execute(
            "INSERT INTO produtos_cadastro (nome, sku) VALUES (?, ?)",
            ("SNAP PROD", f"SNAP-{sufixo}"),
        ).lastrowid
        conn.commit()
    return int(vid)


def uuid_hex() -> str:
    import uuid

    return uuid.uuid4().hex[:8]


def test_roundtrip_persistir_explicar():
    vid = _variante()
    result = FiscalResult(
        status=EstadoFiscal.CALCULATED,
        cfop="5405",
        csosn="500",
        icms_base=Decimal("1000.00"),
        icms_rate=Decimal("0.1800"),
        rule_id=77,
        rule_version=1,
        legal_reference="Consulta SEF/MG 105/2021",
        source_url="https://www.legisweb.com.br/legislacao/?id=415741",
    )
    sid = persistir(
        documento_tipo="nfce-teste",
        documento_id=424242,
        document_number="NFCe-424242",
        variante_id=vid,
        produto_nome="Cabo Flexível 2,5mm",
        operation_date="2026-08-23",
        result=result,
        bases={"icms": "1000.00"},
        rates={"icms": "18.0000"},
        values={"icms_st": "0.00"},
        inputs={"quantidade": "10", "unit_price": "100.00"},
    )
    assert sid is not None and sid > 0

    snaps = explicar("nfce-teste", 424242)
    assert len(snaps) == 1
    s = snaps[0]
    assert s["cfop"] == "5405" and s["csosn"] == "500"
    assert s["rule_id"] == 77
    assert s["legal_reference"].startswith("Consulta SEF/MG")
    assert s["bases"]["icms"] == "1000.00"
    assert s["status"] == "CALCULATED"


def test_persistir_falha_retorna_none(monkeypatch):
    from catalog_server.fiscal import snapshot as snap_mod

    def _boom(*a, **k):
        raise RuntimeError("db fora")

    monkeypatch.setattr(snap_mod, "system_conn", _boom)
    r = FiscalResult(status=EstadoFiscal.CALCULATED)
    assert snap_mod.persistir(
        documento_tipo="x", documento_id=1, result=r
    ) is None
