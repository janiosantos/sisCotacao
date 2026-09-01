"""Parâmetros de planejamento por produto/depósito (EST-005).

Política, mínimo/máximo, ponto de pedido, estoque de segurança, lead time,
lote (min/max/múltiplo), calendário e fonte do valor. `obter_efetivo` faz
fallback para os campos legados `estoque_saldo.estoque_minimo/maximo`.
"""

from __future__ import annotations

from catalog_server.db import system_conn

_COLUNAS = (
    "id, produto_id, deposito_id, politica, minimo, maximo, ponto_pedido, "
    "estoque_seguranca, lead_time_dias, lote_minimo, lote_maximo, lote_multiplo, "
    "calendario, fonte_valor, motivo, ativo, versao, criado_em, atualizado_em"
)


def listar(produto_id: int, deposito_id: int | None = None) -> list[dict]:
    sql = f"SELECT {_COLUNAS} FROM estoque_parametro WHERE produto_id=? AND ativo"
    params: list = [produto_id]
    if deposito_id:
        sql += " AND deposito_id=?"
        params.append(deposito_id)
    sql += " ORDER BY deposito_id"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]


def salvar(
    produto_id: int,
    deposito_id: int,
    politica: str,
    minimo: float | None,
    maximo: float | None,
    ponto_pedido: float | None,
    estoque_seguranca: float | None,
    lead_time_dias: int | None,
    lote_minimo: float | None,
    lote_maximo: float | None,
    lote_multiplo: float | None,
    calendario: str | None,
    fonte_valor: str,
    motivo: str | None,
    usuario_id: int | None,
) -> dict:
    politica = (politica or "manual").strip().lower()
    fonte_valor = (fonte_valor or "manual").strip().lower()
    if politica not in ("manual", "calculada"):
        raise ValueError("politica inválida")
    if fonte_valor not in ("manual", "abc", "lead_time_real", "custom"):
        raise ValueError("fonte_valor inválida")
    with system_conn() as conn:
        ativo = conn.execute(
            "SELECT id, versao FROM estoque_parametro"
            " WHERE produto_id=? AND deposito_id=? AND ativo",
            (produto_id, deposito_id),
        ).fetchone()
        nova_versao = int(ativo["versao"]) + 1 if ativo else 1
        if ativo:
            conn.execute(
                "UPDATE estoque_parametro SET ativo=FALSE, atualizado_em=NOW() WHERE id=?",
                (ativo["id"],),
            )
        novo_id = conn.execute(
            "INSERT INTO estoque_parametro "
            "(produto_id, deposito_id, politica, minimo, maximo, ponto_pedido, "
            "estoque_seguranca, lead_time_dias, lote_minimo, lote_maximo, lote_multiplo, "
            "calendario, fonte_valor, motivo, ativo, versao, criado_por) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,TRUE,?,?) RETURNING id",
            (
                produto_id, deposito_id, politica, minimo, maximo, ponto_pedido,
                estoque_seguranca, lead_time_dias, lote_minimo, lote_maximo, lote_multiplo,
                (calendario or "").strip() or None,
                fonte_valor, (motivo or "").strip() or None,
                nova_versao, usuario_id,
            ),
        ).fetchone()["id"]
        r = conn.execute(
            f"SELECT {_COLUNAS} FROM estoque_parametro WHERE id=?", (novo_id,)
        ).fetchone()
        return dict(r)


def excluir(produto_id: int, deposito_id: int) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE estoque_parametro SET ativo=FALSE, atualizado_em=NOW() "
            "WHERE produto_id=? AND deposito_id=? AND ativo",
            (produto_id, deposito_id),
        )
        return cur.rowcount > 0


def obter_efetivo(produto_id: int, deposito_id: int) -> dict:
    """Parâmetro efetivo: configuração nova com fallback para mínimo/máximo legados."""
    with system_conn() as conn:
        row = conn.execute(
            f"SELECT {_COLUNAS} FROM estoque_parametro"
            " WHERE produto_id=? AND deposito_id=? AND ativo ORDER BY versao DESC LIMIT 1",
            (produto_id, deposito_id),
        ).fetchone()
        legado = conn.execute(
            "SELECT estoque_minimo, estoque_maximo FROM estoque_saldo"
            " WHERE produto_id=? AND deposito_id=?",
            (produto_id, deposito_id),
        ).fetchone()
    if row:
        d = dict(row)
        d["minimo_origem"] = "parametro"
        return d
    return {
        "produto_id": produto_id,
        "deposito_id": deposito_id,
        "politica": "manual",
        "minimo": float(legado["estoque_minimo"]) if legado and legado["estoque_minimo"] else None,
        "maximo": float(legado["estoque_maximo"]) if legado and legado["estoque_maximo"] else None,
        "minimo_origem": "legado",
        "fonte_valor": "manual",
    }