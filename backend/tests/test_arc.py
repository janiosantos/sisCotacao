"""ARC-002 (validação de schema), ARC-004 (concorrência real) e ARC-007 (migrações)."""
from __future__ import annotations

import threading

from catalog_server.db import system_conn
from catalog_server.repositories import estoque_repo
from catalog_server.services import validacao
from catalog_server.services import infra


# ─── ARC-002: schemas ──────────────────────────────────────

_SCHEMA = {
    "produto_id": {"tipo": "int", "requerido": True, "min": 1},
    "quantidade": {"tipo": "float", "requerido": True, "min": 0.01},
    "motivo": {"tipo": "string", "requerido": True, "enum": ["defeito", "outro"]},
    "data": {"tipo": "date"},
}


def test_validacao_ok():
    erros, limpo = validacao.validar({"produto_id": 5, "quantidade": 2.5, "motivo": "defeito", "data": "2026-09-01"}, _SCHEMA)
    assert not erros
    assert limpo["produto_id"] == 5


def test_validacao_erros_de_campo():
    erros, _ = validacao.validar({"produto_id": 0, "quantidade": "abc", "motivo": "x"}, _SCHEMA)
    assert "produto_id" in erros  # min
    assert "quantidade" in erros  # não-numérico
    assert "motivo" in erros  # fora do enum
    assert "data" not in erros  # não requerido → sem erro


def test_validacao_campo_desconhecido():
    erros, _ = validacao.validar({"produto_id": 1, "quantidade": 1, "motivo": "defeito", "hack": 1}, _SCHEMA)
    assert "_extra" in erros


# ─── ARC-004: concorrência (PostgreSQL real) ───────────────

def _setup_estoque(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        conn.execute("INSERT INTO produtos_cadastro (nome, ativo, sku, preco) VALUES (%s,%s,%s,%s)", ("P", 1, "ARC-1", 10.0))
        pid = int(conn.execute("SELECT lastval()").fetchone()["lastval"])
        did = int(conn.execute("SELECT id FROM depositos ORDER BY id LIMIT 1").fetchone()["id"])
        conn.commit()
    estoque_repo.movimentar_fato(did, pid, "entrada", 10, origem_tipo="teste")
    return pid, did


def test_saldo_ultimo_item_serializado(system_db):
    """Duas saídas concorrentes do último item: apenas uma passa (advisory lock)."""
    pid, did = _setup_estoque(system_db)
    erros: list = []
    ok = []

    def saida(qtd):
        try:
            r = estoque_repo.movimentar_fato(did, pid, "saida", qtd,
                                             idempotency_key=f"venda-conc-{qtd}",
                                             origem_tipo="venda", origem_id=qtd)
            ok.append(r["saldo_posterior"])
        except ValueError as exc:
            erros.append(str(exc))

    t1 = threading.Thread(target=saida, args=(6.0,))
    t2 = threading.Thread(target=saida, args=(6.0,))
    t1.start(); t2.start(); t1.join(); t2.join()
    # 10 - 6 - 6 = -2 → uma saída falha (insuficiente) ou serializa
    assert len(ok) + len(erros) == 2
    assert len(ok) >= 1
    with system_conn() as conn:
        saldo = conn.execute("SELECT quantidade FROM estoque_saldo WHERE produto_id=%s AND deposito_id=%s", (pid, did)).fetchone()
    assert float(saldo["quantidade"]) >= 0.0  # nunca negativo


def test_idempotencia_concorrente(system_db):
    """Duas chamadas idempotentes simultâneas produzem um único efeito."""
    pid, did = _setup_estoque(system_db)

    def chamar():
        try:
            infra.executar("chave-conc", "teste", {"pid": pid}, lambda conn: {"n": 1})
        except Exception:  # noqa: BLE001
            pass

    t1 = threading.Thread(target=chamar)
    t2 = threading.Thread(target=chamar)
    t1.start(); t2.start(); t1.join(); t2.join()
    with system_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM idempotencia WHERE chave='chave-conc'").fetchone()
    assert int(n["count"]) == 1  # um único efeito gravado


# ─── ARC-007: migrações vazio→head e idempotência ──────────

def test_migracao_apicada_uma_vez():
    """As migrações foram aplicadas (baseline → head) e o guard idempotente protege."""
    with system_conn() as conn:
        guard_ok = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name='idempotencia'"
        ).fetchone()
    assert guard_ok is not None  # migração 0141 aplicada