"""Rastreabilidade de lote/série (EST-008): status, origem, custo, fornecedor,
documento, controle por família, FEFO e recall via ledger.
"""

from __future__ import annotations

from datetime import date

from catalog_server.db import system_conn


def familia_controla_lote(produto_id: int) -> bool:
    """DECISAO-011: lote/série parametrizado por família."""
    with system_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(f.controle_lote, FALSE) AS controle"
            " FROM produtos_cadastro p LEFT JOIN familias f ON f.id=p.familia_id"
            " WHERE p.id=?",
            (produto_id,),
        ).fetchone()
    return bool(row and row["controle"])


def status_derivado(lote: dict) -> str:
    """'vencido' deriva da data de validade; 'bloqueado' é manual; senão 'ativo'."""
    if (lote.get("data_validade") or "").strip():
        try:
            v = lote["data_validade"].strip()[:10]
            if v <= date.today().isoformat():
                return "vencido"
        except (TypeError, ValueError):
            pass
    return (lote.get("status") or "ativo") if lote.get("status") in ("ativo", "bloqueado") else "ativo"


def criar_lote(
    deposito_id: int,
    produto_id: int,
    codigo: str,
    quantidade: float = 0,
    data_fabricacao: str | None = None,
    data_validade: str | None = None,
    custo_unitario: float | None = None,
    fornecedor_id: int | None = None,
    documento: str | None = None,
    origem: str = "avulsa",
    observacao: str | None = None,
) -> int:
    origem = (origem or "avulsa").strip().lower()
    if origem not in ("compra", "producao", "avulsa"):
        raise ValueError("origem inválida")
    with system_conn() as conn:
        lote_id = conn.execute(
            "INSERT INTO lotes (deposito_id, produto_id, codigo, quantidade,"
            " data_fabricacao, data_validade, custo_unitario, fornecedor_id,"
            " documento, origem, observacao)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
            (deposito_id, produto_id, codigo.strip(), quantidade,
             (data_fabricacao or "").strip() or None, (data_validade or "").strip() or None,
             custo_unitario, fornecedor_id, (documento or "").strip() or None,
             origem, (observacao or "").strip() or None),
        ).fetchone()["id"]
        if quantidade and quantidade > 0:
            # entrada do lote no ledger, na MESMA transação (FK lote_id)
            from catalog_server.repositories import estoque_repo
            estoque_repo.movimentar_fato(
                deposito_id, produto_id, "entrada", quantidade,
                idempotency_key=f"lote-{lote_id}-entrada",
                origem_tipo="lote", origem_id=lote_id,
                documento=documento, lote_id=lote_id,
                custo_unitario=custo_unitario,
                observacao=f"entrada de lote {codigo.strip()}",
                _conn=conn,
            )
        return lote_id


def atualizar_status(lote_id: int, status: str) -> bool:
    status = (status or "").strip().lower()
    if status not in ("ativo", "bloqueado"):
        raise ValueError("status inválido (ativo|bloqueado)")
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE lotes SET status=? WHERE id=? AND status<>?", (status, lote_id, status)
        )
        return cur.rowcount > 0


def validar_para_saida(lote_id: int) -> None:
    """Lança ValueError se o lote estiver vencido ou bloqueado (não é vendido)."""
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM lotes WHERE id=?", (lote_id,)).fetchone()
    if not row:
        raise ValueError("Lote não encontrado")
    derivado = status_derivado(dict(row))
    if derivado in ("vencido", "bloqueado"):
        raise ValueError(f"Lote {row['codigo']} está {derivado} — não pode ser usado em saída")


def fefo(produto_id: int, deposito_id: int, quantidade: float, conn=None) -> list[dict]:
    """Alocação FEFO (primeiro a vencer, primeiro a sair) para produtos controlados.

    Retorna `[{lote_id, codigo, quantidade, data_validade}]` respeitando o saldo
    de cada lote; lança ValueError se o total disponível for insuficiente.
    """
    q = float(quantidade)
    if q <= 0:
        raise ValueError("Quantidade deve ser positiva")
    ctx = system_conn() if conn is None else None
    conn2 = conn or ctx.__enter__()
    try:
        rows = conn2.execute(
            "SELECT * FROM lotes WHERE produto_id=? AND deposito_id=? AND quantidade>0"
            " AND status='ativo' AND (data_validade IS NULL OR data_validade >= ?)"
            " ORDER BY data_validade ASC NULLS LAST, id ASC",
            (produto_id, deposito_id, date.today().isoformat()),
        ).fetchall()
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)
    alocacao: list[dict] = []
    restante = q
    for r in rows:
        if restante <= 0:
            break
        disp = float(r["quantidade"] or 0)
        if disp <= 0:
            continue
        usar = min(disp, restante)
        alocacao.append({"lote_id": r["id"], "codigo": r["codigo"], "quantidade": usar,
                         "data_validade": r["data_validade"]})
        restante -= usar
    if restante > 0:
        raise ValueError(
            f"Estoque em lote disponível insuficiente para FEFO: faltam {restante:g}"
        )
    return alocacao


def recall(produto_id: int, lote_id: int | None = None) -> list[dict]:
    """Clientes e documentos afetados por lote (via ledger): saídas com lote
    vinculadas a venda (origem_tipo='venda') → orçamento → cliente."""
    with system_conn() as conn:
        sql = (
            "SELECT m.lote_id, l.codigo AS lote, m.quantidade, m.criado_em,"
            " o.id AS orcamento_id, o.numero AS orcamento_numero, o.criado_em AS data,"
            " c.id AS cliente_id, c.nome AS cliente, c.doc AS cliente_doc"
            " FROM estoque_movimento m"
            " JOIN lotes l ON l.id=m.lote_id"
            " JOIN orcamentos o ON o.id=m.origem_id AND m.origem_tipo='venda'"
            " JOIN clientes c ON c.id=o.cliente_id"
            " WHERE m.produto_id=? AND m.tipo IN ('saida','transferencia')"
        )
        args: list = [produto_id]
        if lote_id:
            sql += " AND m.lote_id=?"
            args.append(lote_id)
        sql += " ORDER BY m.criado_em DESC"
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]