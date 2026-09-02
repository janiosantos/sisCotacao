"""Migração 0143 — crediário aprovado e trilha de decisão.

`credito_cliente` já é o ledger de créditos de devolução/RMA. O crediário
precisa de uma fonte separada para não transformar limite cadastral em crédito
aprovado por acidente.
"""
from __future__ import annotations

import json

VERSION = 143
RISCO = "moderada"  # Expand: tabelas novas e catálogo RBAC
NAME = "crediario_aprovacao"

MUDANCA = {
    "o_que": [
        "Cria credito_aprovacao por cliente com status, limite, validade e responsável",
        "Cria credito_evento append-only para histórico de decisões",
        "Cria credito_reserva para impedir consumo concorrente do limite",
        "Adiciona o recurso RBAC credito e o perfil Financeiro",
    ],
    "porque": [
        "Limite cadastral não é aprovação de crediário",
        "Aprovação, bloqueio e suspensão precisam de autoria e histórico",
        "Vendas concorrentes não podem ultrapassar o limite aprovado",
    ],
}


def guard(conn) -> bool:
    return conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='credito_aprovacao'"
    ).fetchone() is not None


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS credito_aprovacao (
            id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL UNIQUE REFERENCES clientes(id),
            status VARCHAR(20) NOT NULL DEFAULT 'nao_solicitado',
            limite_aprovado NUMERIC(14,2) NOT NULL DEFAULT 0,
            prazo_maximo_dias INTEGER NOT NULL DEFAULT 0,
            condicoes_permitidas JSONB NOT NULL DEFAULT '[]'::jsonb,
            vigencia_inicio DATE,
            vigencia_fim DATE,
            aprovado_por INTEGER REFERENCES usuarios(id),
            aprovado_em TIMESTAMPTZ,
            bloqueado_por INTEGER REFERENCES usuarios(id),
            bloqueado_em TIMESTAMPTZ,
            motivo_bloqueio TEXT,
            versao INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER REFERENCES usuarios(id),
            updated_by INTEGER REFERENCES usuarios(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_credito_aprovacao_status CHECK (
                status IN ('nao_solicitado','em_analise','aprovado','suspenso','reprovado','expirado','bloqueado')
            ),
            CONSTRAINT chk_credito_aprovacao_limite CHECK (limite_aprovado >= 0),
            CONSTRAINT chk_credito_aprovacao_prazo CHECK (prazo_maximo_dias >= 0),
            CONSTRAINT chk_credito_aprovacao_vigencia CHECK (
                vigencia_fim IS NULL OR vigencia_inicio IS NULL OR vigencia_fim >= vigencia_inicio
            )
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS credito_evento (
            id BIGSERIAL PRIMARY KEY,
            credito_id BIGINT NOT NULL REFERENCES credito_aprovacao(id),
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            tipo_evento VARCHAR(30) NOT NULL,
            status_anterior VARCHAR(20),
            status_novo VARCHAR(20) NOT NULL,
            limite_anterior NUMERIC(14,2),
            limite_novo NUMERIC(14,2),
            motivo TEXT,
            documentos_ref JSONB NOT NULL DEFAULT '[]'::jsonb,
            snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            usuario_id INTEGER REFERENCES usuarios(id),
            ip VARCHAR(45),
            correlation_id VARCHAR(64),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS credito_reserva (
            id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            credito_id BIGINT NOT NULL REFERENCES credito_aprovacao(id),
            orcamento_id BIGINT NOT NULL UNIQUE REFERENCES orcamentos(id),
            valor NUMERIC(14,2) NOT NULL,
            status VARCHAR(15) NOT NULL DEFAULT 'reservada',
            expira_em TIMESTAMPTZ NOT NULL,
            criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            liberada_em TIMESTAMPTZ,
            CONSTRAINT chk_credito_reserva_valor CHECK (valor > 0),
            CONSTRAINT chk_credito_reserva_status CHECK (status IN ('reservada','consumida','liberada','cancelada'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_credito_evento_cliente ON credito_evento (cliente_id, criado_em DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_credito_reserva_ativa ON credito_reserva (cliente_id, status, expira_em)")

    # Backfill conservador: limite antigo nunca vira aprovação automática.
    conn.execute(
        """
        INSERT INTO credito_aprovacao (cliente_id, status, limite_aprovado, created_by, updated_by)
        SELECT c.id, CASE WHEN COALESCE(c.limite_credito, 0) > 0 THEN 'em_analise' ELSE 'nao_solicitado' END,
               0, NULL, NULL
          FROM clientes c
         WHERE NOT EXISTS (
               SELECT 1 FROM credito_aprovacao ca WHERE ca.cliente_id = c.id
         )
        """
    )

    conn.execute(
        "INSERT INTO recursos (codigo, nome, grupo) VALUES ('credito','Crediário','Financeiro') "
        "ON CONFLICT (codigo) DO NOTHING"
    )
    conn.execute(
        "INSERT INTO perfis (nome, descricao) VALUES ('Financeiro','Análise e gestão de crédito, contas e conciliação') "
        "ON CONFLICT (nome) DO NOTHING"
    )
    financeiro = conn.execute("SELECT id FROM perfis WHERE nome='Financeiro'").fetchone()
    recurso = conn.execute("SELECT id FROM recursos WHERE codigo='credito'").fetchone()
    if financeiro and recurso:
        conn.execute(
            "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes) VALUES (%s,%s,%s::jsonb) "
            "ON CONFLICT (perfil_id, recurso_id) DO UPDATE SET acoes=EXCLUDED.acoes",
            (financeiro[0], recurso[0], json.dumps(["visualizar", "cadastrar", "editar", "aprovar", "configurar"])),
        )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS credito_reserva")
    conn.execute("DROP TABLE IF EXISTS credito_evento")
    conn.execute("DROP TABLE IF EXISTS credito_aprovacao")
