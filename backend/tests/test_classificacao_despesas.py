"""Regressões da classificação financeira e da competência de preços."""
from __future__ import annotations

from datetime import date

from werkzeug.security import generate_password_hash

from catalog_server import auth_token
from catalog_server.app_factory import create_app
from catalog_server.db import system_conn


def _admin(system_db):
    with system_conn() as conn:
        user = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s) RETURNING id",
            ("Admin Classificacao", "admin_classificacao", generate_password_hash("x123")),
        ).fetchone()
        uid = int(user["id"])
        perfil = conn.execute("SELECT id FROM perfis WHERE nome='Administrador'").fetchone()
        conn.execute("INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s)", (uid, perfil["id"]))
    return create_app().test_client(), {"Authorization": f"Bearer {auth_token.criar_token({'id': uid, 'login': 'admin_classificacao'})}"}


def test_lancamento_pagar_exige_classificacao_e_grava_snapshot(system_db):
    client, headers = _admin(system_db)
    account = client.post("/api/plano-contas", headers=headers, json={
        "codigo": "5.01", "nome": "Aluguel", "tipo": "despesa",
        "natureza_custo": "fixa", "politica_rateio": "ratear_faturamento",
        "permite_rateio": True, "exige_competencia": True,
    })
    assert account.status_code == 201, account.get_json()
    conta_id = account.get_json()["id"]
    result = client.post("/api/financeiro/pagar", headers=headers, json={
        "fornecedor": "Imobiliaria", "valor": 1000, "data_vencimento": date.today().isoformat(),
        "data_emissao": date.today().isoformat(), "competencia": "2026-09",
        "plano_conta_id": conta_id,
    })
    assert result.status_code == 201, result.get_json()
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM contas_pagar WHERE id=%s", (result.get_json()["id"],)).fetchone()
    assert row["status_classificacao"] == "classificada"
    assert row["natureza_custo_snapshot"] == "fixa"
    assert row["politica_rateio_snapshot"] == "ratear_faturamento"
    assert row["elegivel_precificacao"] is True


def test_competencia_apura_fixas_e_variaveis_e_rateio(system_db):
    client, headers = _admin(system_db)
    def conta(codigo, natureza):
        r = client.post("/api/plano-contas", headers=headers, json={
            "codigo": codigo, "nome": codigo, "tipo": "despesa",
            "natureza_custo": natureza, "politica_rateio": "ratear_faturamento",
            "permite_rateio": True,
        })
        assert r.status_code == 201, r.get_json()
        return r.get_json()["id"]

    fixa = conta("5.02", "fixa")
    variavel = conta("5.03", "variavel")
    for plan, value in ((fixa, 250), (variavel, 150)):
        r = client.post("/api/financeiro/pagar", headers=headers, json={
            "fornecedor": "Fornecedor", "valor": value,
            "data_vencimento": "2026-09-30", "competencia": "2026-09",
            "plano_conta_id": plan,
        })
        assert r.status_code == 201, r.get_json()
    r = client.post("/api/financeiro/competencias", headers=headers, json={
        "competencia": "2026-09", "faturamento_base": 10000,
    })
    assert r.status_code == 201, r.get_json()
    assert client.post("/api/financeiro/competencias/2026-09/status", headers=headers, json={"status": "aprovada"}).status_code == 200
    apuracao = client.get("/api/financeiro/competencias/2026-09/apuracao", headers=headers)
    assert apuracao.status_code == 200, apuracao.get_json()
    body = apuracao.get_json()
    assert body["despesas_fixas"] == 250
    assert body["despesas_variaveis"] == 150
    assert body["despesa_variavel_pct"] == 1.5

