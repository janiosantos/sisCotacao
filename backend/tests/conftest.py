"""Fixtures de teste: PostgreSQL (catalog_test) — banco único do ERP.

Os testes exigem `TEST_PG_URL` com a URL de um banco de teste (ex.:
`postgresql+psycopg://catalog:catalog@localhost:5432/catalog_test`). O schema é
aplicado uma vez por sessão e cada teste recebe um banco zerado via
`TRUNCATE ... RESTART IDENTITY CASCADE`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Pacotes vivem em backend/ (catalog_server, migrations) e na raiz (app/scrapper).
_BACKEND = Path(__file__).resolve().parent.parent
_RAIZ = _BACKEND.parent
for _p in (str(_BACKEND), str(_RAIZ)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

TEST_PG_URL = os.getenv("TEST_PG_URL", "")

if not TEST_PG_URL:
    pytest.exit(
        "TEST_PG_URL é obrigatória: os testes do ERP rodam somente contra "
        "PostgreSQL (ex.: TEST_PG_URL='postgresql+psycopg://catalog:catalog@"
        "localhost:5432/catalog_test')",
        returncode=2,
    )

# O ERP é 100% PostgreSQL: `catalog_server.db` lê `DATABASE_URL` no import.
os.environ["DATABASE_URL"] = TEST_PG_URL

from catalog_server import db as db_mod  # noqa: E402


@pytest.fixture(scope="session")
def test_engine():
    """Reutiliza o pool de teste; nao compartilha transacoes entre testes."""
    import sqlalchemy

    engine = sqlalchemy.create_engine(TEST_PG_URL, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def pg_schema(test_engine):
    """Aplica o schema Postgres (baseline + migrações) uma vez por sessão."""
    with test_engine.connect() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
        conn.commit()

    # Mesmo caminho do startup de produção: migrações (a 0091 cria extensões,
    # f_unaccent e os índices pg_trgm da busca por descrição padronizada).
    from catalog_server.db import init_db

    init_db()

    with test_engine.connect() as conn:
        # Seeds replicados das migrações (estado pós-migração):
        conn.exec_driver_sql("INSERT INTO depositos (nome) VALUES ('Matriz')")
        conn.exec_driver_sql("INSERT INTO tabelas_preco (nome, tipo) VALUES ('Tabela Padrão', 'varejo')")
        conn.commit()
    return True


@pytest.fixture()
def system_db(pg_schema, test_engine, pg_tables):
    """Zera as tabelas do banco de teste PG antes de cada teste.

    Os testes assumem banco vazio; `DATABASE_URL` já aponta para `TEST_PG_URL`
    (definido no conftest) e as migrações são aplicadas uma vez por processo.
    """
    _truncate_all(test_engine, pg_tables)
    _seed_pg(test_engine)
    return None


@pytest.fixture(scope="session")
def pg_tables(pg_schema, test_engine):
    """Lista estavel das tabelas publicas criada depois das migracoes."""
    with test_engine.connect() as conn:
        return [
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()
        ]


def _truncate_all(engine, tables: list[str]) -> None:
    with engine.connect() as conn:
        if tables:
            conn.exec_driver_sql(
                f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"
            )
        conn.commit()


def _seed_pg(engine) -> None:
    with engine.connect() as conn:
        conn.exec_driver_sql("INSERT INTO depositos (nome) VALUES ('Matriz')")
        conn.exec_driver_sql("INSERT INTO tabelas_preco (nome, tipo) VALUES ('Tabela Padrão', 'varejo')")
        # Seeds de referência fiscal (replicados da migração 0054 — o TRUNCATE
        # por teste apaga os dados aplicados pela migração).
        conn.exec_driver_sql(
            "INSERT INTO cfop (codigo, descricao, tipo) VALUES "
            "('1.102','Compra para industrialização','entrada'),"
            "('1.111','Compra para revenda','entrada'),"
            "('5.102','Venda de mercadoria adquirida','saida')"
            " ON CONFLICT (codigo) DO NOTHING"
        )
        conn.exec_driver_sql(
            "INSERT INTO cst_icms (codigo, descricao) VALUES "
            "('00','Tributada integralmente'),('10','Tributada com ST'),('20','Base reduzida')"
            " ON CONFLICT (codigo) DO NOTHING"
        )
        conn.exec_driver_sql(
            "INSERT INTO cst_pis (codigo, descricao) VALUES "
            "('01','Operação Tributável - Alíquota Básica'),('02','Operação Tributável - Diferenciada')"
            " ON CONFLICT (codigo) DO NOTHING"
        )
        conn.exec_driver_sql(
            "INSERT INTO cst_cofins (codigo, descricao) VALUES "
            "('01','Operação Tributável - Alíquota Básica'),('02','Operação Tributável - Diferenciada')"
            " ON CONFLICT (codigo) DO NOTHING"
        )
        conn.exec_driver_sql(
            "INSERT INTO csosn (codigo, descricao) VALUES "
            "('101','Tributada pelo Simples Nacional com permissão de crédito'),"
            "('102','Tributada pelo Simples Nacional sem permissão de crédito'),"
            "('900','Outros')"
            " ON CONFLICT (codigo) DO NOTHING"
        )
        conn.exec_driver_sql(
            "INSERT INTO beneficios_fiscais (codigo, descricao, tipo, valor_default) VALUES "
            "('ISENCAO','Isenção de ICMS','isencao',0),"
            "('RED_BASE','Redução de base de cálculo ICMS','reducao_base',20),"
            "('CRED_PRES','Crédito presumido de ICMS','credito_presumido',0)"
            " ON CONFLICT (codigo) DO NOTHING"
        )
        # Seeds de controle de acesso (migração 0075 — TRUNCATE por teste apaga).
        _seed_rbac_pg(conn)
        conn.commit()


def _seed_rbac_pg(conn) -> None:
    """Replica os seeds RBAC da migração 0075 (perfis/recursos/matriz)."""
    import json as _json

    perfis = [
        ("Administrador", "Acesso total — ignora as checagens de permissão"),
        ("Vendedor", "Vendas, pré-venda, orçamentos, clientes"),
        ("Estoquista", "Estoque, fiscal e logística"),
        ("Operador", "PDV, caixa e orçamentos"),
    ]
    for nome, desc in perfis:
        conn.exec_driver_sql(
            "INSERT INTO perfis (nome, descricao) VALUES (%s, %s) ON CONFLICT (nome) DO NOTHING",
            (nome, desc),
        )
    recursos = [
        ("dashboard", "Painel", "Vendas"),
        ("catalogo", "Catálogo", "Vendas"),
        ("pre-venda", "Pré-venda (PDV)", "Vendas"),
        ("orcamentos", "Orçamentos", "Vendas"),
        ("cotacoes", "Cotações", "Vendas"),
        ("compras", "Compras", "Vendas"),
        ("clientes", "Clientes", "Cadastros"),
        ("fornecedores", "Fornecedores", "Cadastros"),
        ("produtos", "Produtos", "Cadastros"),
        ("vendedores", "Vendedores", "Cadastros"),
        ("categorias", "Categorias", "Cadastros"),
        ("unidades", "Unidades", "Cadastros"),
        ("qualidade", "Qualidade do catálogo", "Cadastros"),
        ("financeiro", "Financeiro", "Financeiro"),
        ("caixa", "Caixa", "Financeiro"),
        ("precos", "Preços", "Financeiro"),
        ("bancos", "Bancos", "Financeiro"),
        ("plano_contas", "Plano de contas", "Financeiro"),
        ("estoque", "Estoque", "Logística"),
        ("fiscal", "Fiscal", "Logística"),
        ("posvenda", "Pós-venda", "Admin"),
        ("solicitacoes", "Solicitações de compra", "Admin"),
        ("historico", "Histórico de preços", "Admin"),
        ("usuarios", "Usuários", "Admin"),
        ("perfis", "Perfis e permissões", "Admin"),
        ("configuracoes", "Configurações", "Admin"),
        ("atualizacoes", "Atualizações", "Admin"),
        ("contabil", "Contábil (gatilhos)", "Admin"),
        ("impressao", "Impressão", "Admin"),
        ("credito", "Crediário", "Financeiro"),
    ]
    for codigo, nome, grupo in recursos:
        conn.exec_driver_sql(
            "INSERT INTO recursos (codigo, nome, grupo) VALUES (%s, %s, %s)"
            " ON CONFLICT (codigo) DO NOTHING",
            (codigo, nome, grupo),
        )
    presets = {
        "Vendedor": {
            "dashboard": ["visualizar"],
            "catalogo": ["visualizar"],
            "pre-venda": ["visualizar", "cadastrar", "editar", "imprimir"],
            "orcamentos": ["visualizar", "cadastrar", "editar", "imprimir"],
            "cotacoes": ["visualizar"],
            "clientes": ["visualizar", "cadastrar", "editar"],
            "precos": ["visualizar"],
            "impressao": ["imprimir"],
            "credito": ["visualizar", "cadastrar"],
        },
        "Estoquista": {
            "dashboard": ["visualizar"],
            "produtos": ["visualizar"],
            "estoque": ["visualizar", "cadastrar", "editar", "excluir", "imprimir"],
            "fiscal": ["visualizar"],
            "qualidade": ["visualizar"],
            "solicitacoes": ["visualizar", "cadastrar"],
            "compras": ["visualizar"],
            "impressao": ["imprimir"],
        },
        "Operador": {
            "dashboard": ["visualizar"],
            "pre-venda": ["visualizar", "cadastrar", "editar", "imprimir"],
            "orcamentos": ["visualizar", "cadastrar", "editar", "imprimir"],
            "caixa": ["visualizar", "cadastrar"],
            "clientes": ["visualizar"],
            "produtos": ["visualizar"],
            "estoque": ["visualizar"],
            "fiscal": ["visualizar", "emitir"],
            "impressao": ["imprimir"],
        },
    }
    for nome_perfil, matriz in presets.items():
        row = conn.exec_driver_sql(
            "SELECT id FROM perfis WHERE nome=%s", (nome_perfil,)
        ).fetchone()
        if not row:
            continue
        pid = row[0]
        for codigo, acoes in matriz.items():
            rrow = conn.exec_driver_sql(
                "SELECT id FROM recursos WHERE codigo=%s", (codigo,)
            ).fetchone()
            if not rrow:
                continue
            conn.exec_driver_sql(
                "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes)"
                " VALUES (%s, %s, %s::jsonb) ON CONFLICT DO NOTHING",
                (pid, rrow[0], _json.dumps(acoes)),
            )


@pytest.fixture()
def conn(system_db):
    """Conexão aberta com o banco de teste (mesmo contrato do `system_conn`)."""
    with db_mod.system_conn() as c:
        yield c
