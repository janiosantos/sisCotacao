"""Migração 0146 — rede de parceiros profissionais e fidelização auditável."""
from __future__ import annotations

import json

VERSION = 146
RISCO = "moderada"
NAME = "programa_parceiros"

MUDANCA = {
    "o_que": [
        "Cria cadastro operacional de parceiros profissionais",
        "Cria indicações, ledger de pontos e bônus com aprovação",
        "Cria política versionada de pontuação e bonificação",
        "Adiciona o recurso RBAC parceiros",
    ],
    "porque": [
        "Parcerias precisam de rastreabilidade por cliente, venda e responsável",
        "Pontos e bônus não podem ser saldos alterados diretamente pela UI",
    ],
}


def guard(conn) -> bool:
    names = {r[0] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name IN "
        "('parceiro_profissional','parceiro_indicacao','parceiro_ponto','parceiro_bonus','parceiro_politica')"
    ).fetchall()}
    return len(names) == 5


def forward(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parceiro_profissional (
            id BIGSERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL UNIQUE REFERENCES clientes(id),
            codigo VARCHAR(30) NOT NULL UNIQUE,
            categoria VARCHAR(30) NOT NULL DEFAULT 'outro',
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            nivel VARCHAR(20) NOT NULL DEFAULT 'bronze',
            observacao TEXT,
            aprovado_por INTEGER REFERENCES usuarios(id),
            aprovado_em TIMESTAMPTZ,
            bloqueado_por INTEGER REFERENCES usuarios(id),
            bloqueado_em TIMESTAMPTZ,
            criado_por INTEGER REFERENCES usuarios(id),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_parceiro_categoria CHECK (categoria IN ('eletricista','encanador','instalador','construtor','arquiteto','engenheiro','revenda','outro')),
            CONSTRAINT chk_parceiro_status CHECK (status IN ('pendente','ativo','suspenso','bloqueado','inativo')),
            CONSTRAINT chk_parceiro_nivel CHECK (nivel IN ('bronze','prata','ouro','platina'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parceiro_indicacao (
            id BIGSERIAL PRIMARY KEY,
            parceiro_id BIGINT NOT NULL REFERENCES parceiro_profissional(id),
            codigo VARCHAR(40) NOT NULL UNIQUE,
            cliente_id INTEGER REFERENCES clientes(id),
            status VARCHAR(20) NOT NULL DEFAULT 'registrada',
            orcamento_id BIGINT UNIQUE REFERENCES orcamentos(id),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            convertido_em TIMESTAMPTZ,
            CONSTRAINT chk_indicacao_status CHECK (status IN ('registrada','convertida','cancelada'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parceiro_ponto (
            id BIGSERIAL PRIMARY KEY,
            parceiro_id BIGINT NOT NULL REFERENCES parceiro_profissional(id),
            tipo VARCHAR(15) NOT NULL,
            pontos NUMERIC(14,2) NOT NULL,
            origem_tipo VARCHAR(30),
            origem_id BIGINT,
            idempotency_key VARCHAR(100) UNIQUE,
            observacao TEXT,
            usuario_id INTEGER REFERENCES usuarios(id),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_parceiro_ponto_tipo CHECK (tipo IN ('credito','debito','expiracao','ajuste')),
            CONSTRAINT chk_parceiro_ponto_valor CHECK (pontos > 0)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parceiro_bonus (
            id BIGSERIAL PRIMARY KEY,
            parceiro_id BIGINT NOT NULL REFERENCES parceiro_profissional(id),
            indicacao_id BIGINT REFERENCES parceiro_indicacao(id),
            orcamento_id BIGINT REFERENCES orcamentos(id),
            valor NUMERIC(14,2) NOT NULL,
            status VARCHAR(15) NOT NULL DEFAULT 'pendente',
            aprovado_por INTEGER REFERENCES usuarios(id),
            aprovado_em TIMESTAMPTZ,
            pago_por INTEGER REFERENCES usuarios(id),
            pago_em TIMESTAMPTZ,
            motivo TEXT,
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_parceiro_bonus_origem UNIQUE (parceiro_id, indicacao_id, orcamento_id),
            CONSTRAINT chk_parceiro_bonus_status CHECK (status IN ('pendente','aprovado','pago','cancelado')),
            CONSTRAINT chk_parceiro_bonus_valor CHECK (valor > 0)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parceiro_politica (
            id BIGSERIAL PRIMARY KEY,
            categoria VARCHAR(30) NOT NULL DEFAULT 'outro',
            percentual_bonus NUMERIC(8,4) NOT NULL DEFAULT 1,
            pontos_por_real NUMERIC(8,4) NOT NULL DEFAULT 1,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            versao INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER REFERENCES usuarios(id),
            criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_parceiro_politica UNIQUE (categoria, versao),
            CONSTRAINT chk_parceiro_bonus_pct CHECK (percentual_bonus >= 0 AND percentual_bonus <= 100),
            CONSTRAINT chk_parceiro_pontos_real CHECK (pontos_por_real >= 0)
        )
        """
    )
    conn.execute(
        "INSERT INTO parceiro_politica (categoria, percentual_bonus, pontos_por_real, versao) "
        "VALUES ('outro', 1, 1, 1) ON CONFLICT (categoria, versao) DO NOTHING"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_parceiro_indicacao_status ON parceiro_indicacao (parceiro_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_parceiro_ponto_data ON parceiro_ponto (parceiro_id, criado_em DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_parceiro_bonus_status ON parceiro_bonus (status, criado_em DESC)")
    conn.execute(
        "INSERT INTO recursos (codigo, nome, grupo) VALUES ('parceiros','Parceiros e fidelização','Comercial') "
        "ON CONFLICT (codigo) DO NOTHING"
    )
    conn.execute(
        "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes) "
        "SELECT p.id, r.id, %s::jsonb FROM perfis p CROSS JOIN recursos r "
        "WHERE p.nome IN ('Administrador','Vendedor') AND r.codigo='parceiros' "
        "ON CONFLICT (perfil_id, recurso_id) DO NOTHING",
        (json.dumps(["visualizar", "cadastrar", "editar"]),),
    )
    conn.commit()


def backward(conn) -> None:
    conn.execute("DROP TABLE IF EXISTS parceiro_bonus")
    conn.execute("DROP TABLE IF EXISTS parceiro_ponto")
    conn.execute("DROP TABLE IF EXISTS parceiro_indicacao")
    conn.execute("DROP TABLE IF EXISTS parceiro_politica")
    conn.execute("DROP TABLE IF EXISTS parceiro_profissional")
