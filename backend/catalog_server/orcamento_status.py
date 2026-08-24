"""Lifecycle orçamento→pedido (migração 0078).

Orçamento (proposta, editável): rascunho/ativo/em_analise/liberado.
Pedido (compromisso, congelado): finalizado/recebido/cancelado/devolvido.

Regras:
- Conteúdo (cliente, itens, desconto, condição…) só é editável até `liberado`.
- `liberado → finalizado` é a conversão orçamento→pedido (gate de alçada,
  estoque e fiscal rodam no blueprint antes de transicionar).
- A partir de `finalizado`, não há edição de conteúdo; correção via `reabrir`
  (com permissão) que volta para `liberado` (ou `em_analise`).
- Transições são explícitas — sem <select> livre de status.
"""
from __future__ import annotations

from catalog_server.db import system_conn

# Orçamento (proposta) — editável.
ORCAMENTO_STATUS = ("rascunho", "ativo", "em_analise", "liberado")
# Pedido (compromisso) — congelado.
PEDIDO_STATUS = ("finalizado", "recebido", "cancelado", "devolvido")

STATUS_LIST = ORCAMENTO_STATUS + PEDIDO_STATUS

# Mapa de transições permitidas origem -> destinos válidos.
_TRANSICOES: dict[str, tuple[str, ...]] = {
    "rascunho": ("ativo", "em_analise", "liberado", "finalizado", "cancelado"),
    "ativo": ("rascunho", "em_analise", "liberado", "finalizado", "cancelado"),
    "em_analise": ("rascunho", "ativo", "liberado", "finalizado", "cancelado"),
    "liberado": ("em_analise", "finalizado", "cancelado"),
    "finalizado": ("recebido", "cancelado", "devolvido", "liberado"),  # liberado = reabrir
    "recebido": ("cancelado", "devolvido"),
    "cancelado": (),
    "devolvido": (),
}

# Status que permitem edição de conteúdo (cliente/itens/desconto/condição).
EDITAVEIS = ("rascunho", "ativo", "em_analise", "liberado")


def transicao_valida(origem: str, destino: str) -> bool:
    return destino in _TRANSICOES.get(origem, ())


def pode_editar_conteudo(status: str) -> bool:
    return status in EDITAVEIS


def aplicar_transicao(orcamento_id: int, destino: str) -> bool:
    """Aplica a transição de status se válida; marca virou_pedido na conversão.

    `finalizado` é a conversão orçamento→pedido; `reabrir` (finalizado→liberado)
    desfaz a marcação de pedido.
    """
    with system_conn() as conn:
        row = conn.execute(
            "SELECT status, virou_pedido FROM orcamentos WHERE id=?", (orcamento_id,)
        ).fetchone()
        if row is None:
            return False
        origem = row["status"]
        if not transicao_valida(origem, destino):
            return False
        virou_pedido = row["virou_pedido"] or 0
        if destino == "finalizado":
            virou_pedido = 1
        elif destino in ORCAMENTO_STATUS and origem == "finalizado":
            virou_pedido = 0  # reabrir desfaz a conversão
        conn.execute(
            "UPDATE orcamentos SET status=?, virou_pedido=?, atualizado_em=datetime('now')"
            " WHERE id=?",
            (destino, virou_pedido, orcamento_id),
        )
        conn.commit()
        return True


def obter_transicoes(status: str) -> list[str]:
    return list(_TRANSICOES.get(status, ()))


__all__ = [
    "STATUS_LIST",
    "ORCAMENTO_STATUS",
    "PEDIDO_STATUS",
    "transicao_valida",
    "pode_editar_conteudo",
    "aplicar_transicao",
    "obter_transicoes",
]