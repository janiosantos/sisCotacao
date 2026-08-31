"""Relações entre produtos (MDM-005).

Equivalentes, substitutos, acessórios, complementares e componentes de kit,
com fator, prioridade, vigência, aprovação, motivo e versão. Apenas Expand:
as relações são estrutura de dado; a movimentação de kit (baixa dos
componentes) e a substituição com confirmação na venda pertencem a EST/VEN.
"""

from __future__ import annotations

from decimal import Decimal

from catalog_server.db import system_conn

TIPOS = {"equivalente", "substituto", "acessorio", "complementar", "componente"}

_COLUNAS = (
    "id, produto_id, relacionado_id, tipo, fator, prioridade, vigencia_inicio, "
    "vigencia_fim, aprovado, motivo, ativo, versao, criado_em, atualizado_em"
)
_COLUNAS_P = ", ".join("r." + c for c in _COLUNAS.split(", "))


def _valida(produto_id: int, relacionado_id: int, tipo: str, fator: float) -> None:
    tipo = (tipo or "").strip().lower()
    if tipo not in TIPOS:
        raise ValueError(f"tipo inválido: {tipo}")
    if produto_id == relacionado_id:
        raise ValueError("produto e relacionado devem ser diferentes")
    try:
        f = Decimal(str(fator))
    except (TypeError, ValueError):
        raise ValueError("fator inválido") from None
    if f <= 0:
        raise ValueError("fator deve ser maior que zero")


def listar(produto_id: int, tipo: str | None = None) -> list[dict]:
    sql = (
        f"SELECT {_COLUNAS_P}, p.nome AS relacionado_nome, p.sku AS relacionado_sku "
        "FROM produto_relacao r JOIN produtos_cadastro p ON p.id=r.relacionado_id "
        "WHERE r.produto_id=? AND r.ativo"
    )
    params: list = [produto_id]
    if tipo:
        sql += " AND r.tipo=?"
        params.append((tipo or "").strip().lower())
    sql += " AND (r.vigencia_inicio IS NULL OR r.vigencia_inicio <= CURRENT_DATE)"
    sql += " AND (r.vigencia_fim IS NULL OR r.vigencia_fim >= CURRENT_DATE)"
    sql += " ORDER BY r.tipo, r.prioridade, r.id"
    with system_conn() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]


def relacionados(produto_id: int) -> list[dict]:
    """Relações ativas nos dois sentidos (substitutos/complementares de/para o produto)."""
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.produto_id, r.relacionado_id, r.tipo, r.fator, r.prioridade,
                   r.aprovado, r.motivo,
                   CASE WHEN r.produto_id=? THEN r.relacionado_id ELSE r.produto_id END AS outro_id,
                   p.nome AS outro_nome, p.sku AS outro_sku,
                   CASE WHEN r.produto_id=? THEN 'origem' ELSE 'alvo' END AS direcao
            FROM produto_relacao r
            JOIN produtos_cadastro p ON p.id = CASE WHEN r.produto_id=? THEN r.relacionado_id ELSE r.produto_id END
            WHERE r.ativo AND (r.produto_id=? OR r.relacionado_id=?)
              AND (r.vigencia_inicio IS NULL OR r.vigencia_inicio <= CURRENT_DATE)
              AND (r.vigencia_fim IS NULL OR r.vigencia_fim >= CURRENT_DATE)
            ORDER BY r.tipo, r.prioridade, r.id
            """,
            (produto_id, produto_id, produto_id, produto_id, produto_id),
        ).fetchall()
        return [dict(r) for r in rows]


def salvar(
    produto_id: int,
    relacionado_id: int,
    tipo: str,
    fator: float,
    prioridade: int,
    vigencia_inicio: str | None,
    vigencia_fim: str | None,
    motivo: str | None,
    usuario_id: int | None,
) -> dict:
    _valida(produto_id, relacionado_id, tipo, fator)
    prio = int(prioridade or 1)
    with system_conn() as conn:
        ativo = conn.execute(
            "SELECT id, versao FROM produto_relacao "
            "WHERE produto_id=? AND relacionado_id=? AND tipo=? AND ativo",
            (produto_id, relacionado_id, tipo),
        ).fetchone()
        nova_versao = int(ativo["versao"]) + 1 if ativo else 1
        if ativo:
            conn.execute(
                "UPDATE produto_relacao SET ativo=FALSE, atualizado_em=NOW() WHERE id=?",
                (ativo["id"],),
            )
        novo_id = conn.execute(
            "INSERT INTO produto_relacao "
            "(produto_id, relacionado_id, tipo, fator, prioridade, vigencia_inicio, "
            "vigencia_fim, aprovado, motivo, ativo, versao, criado_por) "
            "VALUES (?,?,?,?,?,?,?,TRUE,?,TRUE,?,?) RETURNING id",
            (
                produto_id,
                relacionado_id,
                tipo,
                Decimal(str(fator)),
                prio,
                vigencia_inicio or None,
                vigencia_fim or None,
                (motivo or "").strip() or None,
                nova_versao,
                usuario_id,
            ),
        ).fetchone()["id"]
        r = conn.execute(
            f"SELECT {_COLUNAS} FROM produto_relacao WHERE id=?", (novo_id,)
        ).fetchone()
        return dict(r)


def excluir(produto_id: int, relacao_id: int) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE produto_relacao SET ativo=FALSE, atualizado_em=NOW() "
            "WHERE id=? AND produto_id=? AND ativo",
            (relacao_id, produto_id),
        )
        return cur.rowcount > 0