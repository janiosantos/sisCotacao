"""Migração 0078 — Lifecycle orçamento→pedido + alçada de desconto (v2.18.0).

Separa os conceitos dentro da mesma tabela:
- Orçamento (proposta, editável): rascunho/ativo/em_analise/liberado.
- Pedido (compromisso, congelado): finalizado/recebido/cancelado/devolvido.
- `faturado` deixa de ser status de transição (vira marcação de NF emitida via
  documentos_fiscais); `virou_pedido` marca o ponto da conversão.

Alçada de desconto:
- `desconto_status` (ok/pendente/aprovado/rejeitado), mantendo
  `desconto_autorizado` (compat).
- `desconto_rejeitado_por/em/motivo`.
- Tabela `desconto_aprovacao_log` (auditoria: aprovar/revogar/rejeitar).

Backfill: `faturado` → `finalizado` (+ virou_pedido=1); `recebido` → recebido
(+ virou_pedido=1).
"""
from __future__ import annotations

VERSION = 78
RISCO = "critica"
NAME = "lifecycle_pedido_alcada"

MUDANCA = {
    "o_que": [
        "Novo lifecycle: orçamento (rascunho..liberado) vs pedido (finalizado..recebido/cancelado/devolvido); virou_pedido marca a conversão",
        "faturado deixa de ser status de transição (emissão fiscal passa a ser controlada por documentos_fiscais)",
        "Alçada de desconto: desconto_status (ok/pendente/aprovado/rejeitado) + rejeitado_por/em/motivo + tabela desconto_aprovacao_log",
        "Backfill: faturado→finalizado e recebido (virou_pedido=1)",
    ],
    "porque": [
        "Separar orçamento (proposta editável) de pedido (compromisso congelado) — conceitos confusos hoje",
        "Gate de alçada dispara na transição liberado→finalizado; edição bloqueada após liberado",
        "Auditar aprovações/revogações/rejeições de desconto acima da alçada",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name='orcamentos' AND column_name='desconto_status'"
    ).fetchone()
    return row is not None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute(
            "ALTER TABLE orcamentos"
            " ADD COLUMN IF NOT EXISTS virou_pedido INTEGER NOT NULL DEFAULT 0"
        )
        conn.execute(
            "ALTER TABLE orcamentos"
            " ADD COLUMN IF NOT EXISTS desconto_status TEXT NOT NULL DEFAULT 'ok'"
        )
        conn.execute(
            "ALTER TABLE orcamentos"
            " ADD COLUMN IF NOT EXISTS desconto_rejeitado_por BIGINT"
            " REFERENCES usuarios(id)"
        )
        conn.execute(
            "ALTER TABLE orcamentos"
            " ADD COLUMN IF NOT EXISTS desconto_rejeitado_em TIMESTAMP"
        )
        conn.execute(
            "ALTER TABLE orcamentos"
            " ADD COLUMN IF NOT EXISTS desconto_rejeitado_motivo TEXT NOT NULL DEFAULT ''"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS desconto_aprovacao_log (
                id BIGSERIAL PRIMARY KEY,
                orcamento_id BIGINT NOT NULL REFERENCES orcamentos(id) ON DELETE CASCADE,
                solicitante_id BIGINT REFERENCES usuarios(id),
                desconto_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
                aprovador_id BIGINT REFERENCES usuarios(id),
                status TEXT NOT NULL DEFAULT 'aprovado',
                motivo TEXT NOT NULL DEFAULT '',
                criado_em TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        # Backfill do lifecycle: faturado vira finalizado; recebido mantém.
        conn.execute(
            "UPDATE orcamentos SET status='finalizado', virou_pedido=1"
            " WHERE status='faturado'"
        )
        conn.execute(
            "UPDATE orcamentos SET virou_pedido=1 WHERE status='recebido'"
        )
        # desconto_status coerente com a autorização existente.
        conn.execute(
            "UPDATE orcamentos SET desconto_status='aprovado'"
            " WHERE desconto_autorizado=1 AND desconto_status='ok'"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        conn.execute("DROP TABLE IF EXISTS desconto_aprovacao_log")
        conn.execute("ALTER TABLE orcamentos DROP COLUMN IF EXISTS desconto_rejeitado_motivo")
        conn.execute("ALTER TABLE orcamentos DROP COLUMN IF EXISTS desconto_rejeitado_em")
        conn.execute("ALTER TABLE orcamentos DROP COLUMN IF EXISTS desconto_rejeitado_por")
        conn.execute("ALTER TABLE orcamentos DROP COLUMN IF EXISTS desconto_status")
        conn.execute("ALTER TABLE orcamentos DROP COLUMN IF EXISTS virou_pedido")
        conn.execute(
            "UPDATE orcamentos SET status='faturado' WHERE status='finalizado'"
        )
    finally:
        conn.autocommit = ac