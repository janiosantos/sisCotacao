"""Migração 0075 — Controle de acesso por perfil (RBAC).

Cria o modelo de permissões: perfis fixos (Vendedor, Estoquista, Operador,
Administrador), catálogo de recursos (módulos), matriz perfil×recurso×ações,
relação N:N usuário×perfil e overrides por usuário (só concedem, nunca negam).

Expand: aditivo — `usuarios.perfil` continua como legado/compatibilidade; o
Administrador é superuser (ignora checagens no serviço de permissão).
"""
from __future__ import annotations

import json

VERSION = 75
RISCO = "rotina"
NAME = "controle_acesso"

MUDANCA = {
    "o_que": [
        "Cria perfis (4 fixos: Administrador, Vendedor, Estoquista, Operador)",
        "Cria recursos (catálogo de módulos) e perfil_recurso (matriz de ações)",
        "Cria usuario_perfis (N:N) e usuario_override (concessões extras por tela)",
        "Backfill: usuários existentes entram no perfil correspondente (admin/vendedor)",
    ],
    "porque": [
        "Controle de acesso por perfil com granularidade de ação (visualizar, cadastrar, editar, excluir, imprimir, aprovar, configurar)",
        "Usuário pode ter múltiplos perfis e acesso personalizado a telas (override concede)",
    ],
}

_ACOES = ["visualizar", "cadastrar", "editar", "excluir", "imprimir", "aprovar", "configurar", "emitir"]

# (codigo, nome, grupo)
_RECURSOS = [
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
]

# Presets por perfil: recurso -> ações.
_PRESETS = {
    "Vendedor": {
        "dashboard": ["visualizar"],
        "catalogo": ["visualizar"],
        "pre-venda": ["visualizar", "cadastrar", "editar", "imprimir"],
        "orcamentos": ["visualizar", "cadastrar", "editar", "imprimir"],
        "cotacoes": ["visualizar"],
        "clientes": ["visualizar", "cadastrar", "editar"],
        "precos": ["visualizar"],
        "impressao": ["imprimir"],
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

# Administrador: superuser — nenhuma linha em perfil_recurso (bypass no serviço).


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name='perfis'"
    ).fetchone() is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS perfis (
                id BIGSERIAL PRIMARY KEY,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT NOT NULL DEFAULT '',
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recursos (
                id BIGSERIAL PRIMARY KEY,
                codigo TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                grupo TEXT NOT NULL DEFAULT '',
                ativo INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS perfil_recurso (
                perfil_id BIGINT NOT NULL REFERENCES perfis(id) ON DELETE CASCADE,
                recurso_id BIGINT NOT NULL REFERENCES recursos(id) ON DELETE CASCADE,
                acoes JSONB NOT NULL DEFAULT '[]',
                PRIMARY KEY (perfil_id, recurso_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuario_perfis (
                usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                perfil_id BIGINT NOT NULL REFERENCES perfis(id) ON DELETE CASCADE,
                PRIMARY KEY (usuario_id, perfil_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuario_override (
                usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                recurso_id BIGINT NOT NULL REFERENCES recursos(id) ON DELETE CASCADE,
                acoes_extra JSONB NOT NULL DEFAULT '[]',
                PRIMARY KEY (usuario_id, recurso_id)
            )
            """
        )

        # Seeds: perfis fixos.
        for nome, desc in (
            ("Administrador", "Acesso total — ignora as checagens de permissão"),
            ("Vendedor", "Vendas, pré-venda, orçamentos, clientes"),
            ("Estoquista", "Estoque, fiscal e logística"),
            ("Operador", "PDV, caixa e orçamentos"),
        ):
            conn.execute(
                "INSERT INTO perfis (nome, descricao) VALUES (%s, %s)"
                " ON CONFLICT (nome) DO NOTHING",
                (nome, desc),
            )

        # Seeds: catálogo de recursos.
        for codigo, nome, grupo in _RECURSOS:
            conn.execute(
                "INSERT INTO recursos (codigo, nome, grupo) VALUES (%s, %s, %s)"
                " ON CONFLICT (codigo) DO NOTHING",
                (codigo, nome, grupo),
            )

        # Seeds: matriz por perfil (Administrador fica sem linhas = superuser).
        for nome_perfil, matriz in _PRESETS.items():
            pid = conn.execute(
                "SELECT id FROM perfis WHERE nome=%s", (nome_perfil,)
            ).fetchone()[0]
            for codigo_recurso, acoes in matriz.items():
                rid = conn.execute(
                    "SELECT id FROM recursos WHERE codigo=%s", (codigo_recurso,)
                ).fetchone()
                if rid is None:
                    continue
                validas = [a for a in acoes if a in _ACOES]
                conn.execute(
                    "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes)"
                    " VALUES (%s, %s, %s::jsonb) ON CONFLICT DO NOTHING",
                    (pid, rid[0], json.dumps(validas)),
                )

        # Backfill: usuários existentes (coluna legada perfil) entram no perfil.
        for row in conn.execute(
            "SELECT id, perfil FROM usuarios WHERE perfil IS NOT NULL"
        ).fetchall():
            nome_perfil = "Administrador" if row[1] == "admin" else "Vendedor"
            pid = conn.execute(
                "SELECT id FROM perfis WHERE nome=%s", (nome_perfil,)
            ).fetchone()
            if pid is None:
                continue
            conn.execute(
                "INSERT INTO usuario_perfis (usuario_id, perfil_id)"
                " VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (row[0], pid[0]),
            )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS usuario_override")
        conn.execute("DROP TABLE IF EXISTS usuario_perfis")
        conn.execute("DROP TABLE IF EXISTS perfil_recurso")
        conn.execute("DROP TABLE IF EXISTS recursos")
        conn.execute("DROP TABLE IF EXISTS perfis")
    finally:
        conn.autocommit = ac
