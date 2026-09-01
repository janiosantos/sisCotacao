"""Base de demanda (COM-003): consolida demanda real/projetada de forma
idempotente (vendas finalizadas, reservas, devoluções, manual), auditável até
os documentos. Separa atendida de perdida por ruptura.
"""

from __future__ import annotations

import uuid
import zlib

from catalog_server.db import system_conn


def consolidar(deposito_id: int | None = None, usuario_id: int | None = None) -> dict:
    """Puxa vendas finalizadas (demanda real atendida) para demanda_registro.
    Idempotente via UNIQUE (origem, origem_id, produto_id). Pedidos cancelados
    não entram (filtro status='finalizado')."""
    vendas = 0
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT oi.produto_id, o.id AS orcamento_id, o.criado_em,
                   SUM(oi.quantidade) AS quantidade, o.cliente_id
            FROM orcamento_itens oi
            JOIN orcamentos o ON o.id=oi.orcamento_id
            WHERE o.status='finalizado'
            GROUP BY oi.produto_id, o.id, o.criado_em, o.cliente_id
            """
        ).fetchall()
        for r in rows:
            cur = conn.execute(
                "INSERT INTO demanda_registro (produto_id, deposito_id, data, quantidade,"
                " tipo, origem, origem_id, status, usuario_id)"
                " VALUES (?,?,?,?,'real','venda',?, 'atendida',?)"
                " ON CONFLICT (origem, origem_id, produto_id) DO NOTHING",
                (r["produto_id"], deposito_id, (r["criado_em"] or "")[:10], r["quantidade"],
                 r["orcamento_id"], usuario_id),
            )
            vendas += cur.rowcount
    return {"inseridas": vendas}


def registrar_manual(
    produto_id: int,
    data: str,
    quantidade: float,
    observacao: str | None = None,
    usuario_id: int | None = None,
    chave_manual: str | None = None,
) -> dict:
    """Registro manual de consumo/demanda projetada. `chave_manual` permite
    idempotência (mesma chave não duplica via UNIQUE origem+origem_id+produto)."""
    chave = chave_manual or f"manual-{produto_id}-{data}-{uuid.uuid4().hex[:8]}"
    origem_id = zlib.crc32(chave.encode("utf-8")) & 0x7FFFFFFF
    with system_conn() as conn:
        id_novo = conn.execute(
            "INSERT INTO demanda_registro (produto_id, data, quantidade, tipo, origem,"
            " origem_id, status, observacao, usuario_id)"
            " VALUES (?,?,?,'real','manual',?,'atendida',?,?) RETURNING id",
            (produto_id, data, float(quantidade), origem_id, observacao, usuario_id),
        ).fetchone()["id"]
    return {"id": id_novo, "produto_id": produto_id, "data": data, "quantidade": float(quantidade)}


def marcar_perdida(demanda_id: int, motivo: str) -> bool:
    """Marca demanda como perdida por ruptura."""
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("motivo é obrigatório")
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE demanda_registro SET status='perdida', motivo_ruptura=? WHERE id=? AND status<>'perdida'",
            (motivo, demanda_id),
        )
        return cur.rowcount > 0


def listar(produto_id: int | None = None, data_inicio: str | None = None, data_fim: str | None = None) -> list[dict]:
    sql = (
        "SELECT d.*, p.sku, p.nome AS produto_nome"
        " FROM demanda_registro d JOIN produtos_cadastro p ON p.id=d.produto_id"
    )
    where: list[str] = []
    args: list = []
    if produto_id:
        where.append("d.produto_id=?")
        args.append(produto_id)
    if data_inicio:
        where.append("d.data >= ?")
        args.append(data_inicio)
    if data_fim:
        where.append("d.data <= ?")
        args.append(data_fim)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY d.data DESC, d.id DESC LIMIT 500"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def auditar(produto_id: int) -> dict:
    """Demanda agregada com origem auditável (documento) e separação atendida/perdida."""
    with system_conn() as conn:
        itens = [dict(r) for r in conn.execute(
            "SELECT d.*, o.numero AS documento, o.criado_em AS documento_em"
            " FROM demanda_registro d LEFT JOIN orcamentos o ON o.id=d.origem_id"
            " WHERE d.produto_id=? ORDER BY d.data DESC LIMIT 500",
            (produto_id,),
        ).fetchall()]
        resumo = dict(conn.execute(
            "SELECT COALESCE(SUM(quantidade) FILTER (WHERE status='atendida'),0) AS atendida,"
            " COALESCE(SUM(quantidade) FILTER (WHERE status='perdida'),0) AS perdida,"
            " COALESCE(SUM(quantidade) FILTER (WHERE status='aberta'),0) AS aberta,"
            " COALESCE(SUM(quantidade),0) AS total"
            " FROM demanda_registro WHERE produto_id=?",
            (produto_id,),
        ).fetchone())
    return {"produto_id": produto_id, "resumo": resumo, "itens": itens}