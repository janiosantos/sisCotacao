"""Rede de parceiros, indicação, pontos e bônus (PAR-001..004)."""
from __future__ import annotations

from catalog_server.db import system_conn
from catalog_server.services import parceiros


def _setup(system_db) -> tuple[int, int]:
    with system_conn() as conn:
        cliente_id = int(conn.execute(
            "INSERT INTO clientes (nome, doc, tipo_pessoa, segmento) VALUES (%s,%s,%s,%s) RETURNING id",
            ("Eletricista Parceiro", "12345678901", "F", "profissional"),
        ).fetchone()["id"])
        vendedor_id = int(conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s) RETURNING id",
            ("Financeiro", "par-fin", "hash"),
        ).fetchone()["id"])
        venda_id = int(conn.execute(
            "INSERT INTO orcamentos (cliente, cliente_id, numero, status, total, total_liquido, desconto, usuario_id) "
            "VALUES (%s,%s,%s,'recebido',1000,1000,0,%s) RETURNING id",
            ("Cliente indicado", cliente_id, "PV-PAR-1", vendedor_id),
        ).fetchone()["id"])
        conn.commit()
    return cliente_id, venda_id


def test_fluxo_indicacao_pontos_bonus(system_db):
    cliente_id, venda_id = _setup(system_db)
    criado = parceiros.criar(cliente_id, "eletricista", usuario_id=1)
    parceiro_id = criado["id"]
    assert criado["status"] == "pendente"
    parceiros.alterar_status(parceiro_id, "ativo", usuario_id=1)

    indicacao = parceiros.criar_indicacao(parceiro_id, cliente_id)
    resultado = parceiros.converter_indicacao(indicacao["id"], venda_id, usuario_id=1)
    assert resultado["bonus"] == 10.0
    assert resultado["pontos"] == 1000

    ledger = parceiros.ledger(parceiro_id)
    assert ledger["saldo_pontos"] == 1000.0
    assert len(ledger["bonus"]) == 1
    assert ledger["bonus"][0]["status"] == "pendente"

    aprovado = parceiros.aprovar_bonus(ledger["bonus"][0]["id"], usuario_id=1)
    assert aprovado["status"] == "aprovado"
    pago = parceiros.pagar_bonus(ledger["bonus"][0]["id"], usuario_id=1)
    assert pago["status"] == "pago"


def test_indicacao_nao_duplica_nem_aceita_venda_aberta(system_db):
    cliente_id, venda_id = _setup(system_db)
    parceiro_id = parceiros.criar(cliente_id, "encanador")["id"]
    parceiros.alterar_status(parceiro_id, "ativo")
    indicacao = parceiros.criar_indicacao(parceiro_id)
    with system_conn() as conn:
        conn.execute("UPDATE orcamentos SET status='rascunho' WHERE id=?", (venda_id,))
        conn.commit()
    try:
        parceiros.converter_indicacao(indicacao["id"], venda_id)
        assert False, "venda aberta não pode gerar bônus"
    except ValueError as exc:
        assert "concluída" in str(exc)
