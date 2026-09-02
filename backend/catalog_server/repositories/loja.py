"""Operações da loja de material (balcão + depósito).

Agrupa: config da loja, saldo/endereçamento, inventário, devolução/troca,
reposição sugerida, comissão de vendedores e dados de etiqueta — evoluindo as
estruturas existentes (estoque_saldo, depositos, variantes, orcamentos).
"""
from __future__ import annotations

from datetime import date, timedelta

from catalog_server.db import system_conn


# ─── Config da loja ───────────────────────────────────────

def get_config() -> dict:
    with system_conn() as conn:
        rows = dict(conn.execute("SELECT chave, valor FROM config_loja").fetchall())
    return {
        "bloquear_venda_sem_estoque": rows.get("bloquear_venda_sem_estoque") == "1",
        "bloquear_venda_sem_credito": rows.get("bloquear_venda_sem_credito") == "1",
        "bloquear_venda_com_atraso": rows.get("bloquear_venda_com_atraso") == "1",
    }


def set_config(chaves: dict) -> dict:
    with system_conn() as conn:
        for chave, valor in chaves.items():
            conn.execute(
                "INSERT INTO config_loja (chave, valor, atualizado_em) VALUES (?,?,datetime('now'))"
                " ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=excluded.atualizado_em",
                (chave, "1" if valor else "0"),
            )
    return get_config()


def bloquear_sem_estoque() -> bool:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT valor FROM config_loja WHERE chave='bloquear_venda_sem_estoque'"
        ).fetchone()
    return row is not None and row["valor"] == "1"


def bloquear_sem_fiscal() -> bool:
    """Bloqueia a finalização quando há erro fiscal "hard" (NCM/CFOP/CST).

    Desativado por padrão enquanto o cadastro fiscal dos produtos ainda está
    sendo populado — ligue via config_loja (`bloquear_venda_sem_fiscal=1`).
    """
    with system_conn() as conn:
        row = conn.execute(
            "SELECT valor FROM config_loja WHERE chave='bloquear_venda_sem_fiscal'"
        ).fetchone()
    return row is not None and row["valor"] == "1"


def bloquear_sem_credito() -> bool:
    """Bloqueia a finalização quando o total da venda excede o limite de
    crédito disponível do cliente (config `bloquear_venda_sem_credito=1`)."""
    with system_conn() as conn:
        row = conn.execute(
            "SELECT valor FROM config_loja WHERE chave='bloquear_venda_sem_credito'"
        ).fetchone()
    return row is not None and row["valor"] == "1"


def bloquear_com_atraso() -> bool:
    """Bloqueia a finalização quando o cliente tem conta em atraso
    (config `bloquear_venda_com_atraso=1`)."""
    with system_conn() as conn:
        row = conn.execute(
            "SELECT valor FROM config_loja WHERE chave='bloquear_venda_com_atraso'"
        ).fetchone()
    return row is not None and row["valor"] == "1"


# ─── Saldo / endereçamento ────────────────────────────────

_CAMPOS_LOGISTICA = ("peso", "dimensoes", "unidade_venda", "embalagem", "fator_conversao", "localizacao")


def atualizar_variante_logistica(produto_id: int, dados: dict) -> bool:
    campos = {k: dados[k] for k in _CAMPOS_LOGISTICA if k in dados}
    if not campos:
        return False
    with system_conn() as conn:
        sets = ", ".join(f"{k}=?" for k in campos)
        cur = conn.execute(
            f"UPDATE produtos_cadastro SET {sets} WHERE id=?",
            list(campos.values()) + [produto_id],
        )
        return cur.rowcount > 0


def atualizar_estoque_localizacao(produto_id: int, deposito_id: int, dados: dict) -> bool:
    campos = {k: dados[k] for k in ("localizacao", "estoque_minimo", "estoque_maximo") if k in dados}
    if not campos:
        return False
    with system_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM estoque_saldo WHERE produto_id=? AND deposito_id=?",
            (produto_id, deposito_id),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO estoque_saldo (produto_id, deposito_id, quantidade) VALUES (?,?,0)",
                (produto_id, deposito_id),
            )
        sets = ", ".join(f"{k}=?" for k in campos)
        conn.execute(
            f"UPDATE estoque_saldo SET {sets}, atualizado_em=datetime('now')"
            " WHERE produto_id=? AND deposito_id=?",
            list(campos.values()) + [produto_id, deposito_id],
        )
        return True


def saldo_variante(produto_id: int) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT s.deposito_id, d.nome AS deposito, s.quantidade AS fisico,"
            " s.reserva AS reservado, s.bloqueado, s.separacao, s.transito,"
            " (s.quantidade - s.reserva - COALESCE(s.bloqueado,0) - COALESCE(s.separacao,0)) AS disponivel,"
            " s.localizacao, s.estoque_minimo, s.estoque_maximo"
            " FROM estoque_saldo s JOIN depositos d ON d.id=s.deposito_id"
            " WHERE s.produto_id=? ORDER BY d.nome",
            (produto_id,),
        ).fetchall()]


def disponibilidade(produto_id: int, deposito_id: int | None = None) -> list[dict]:
    """Fórmula única de disponibilidade (EST-001): físico − reservado − bloqueado − separação.

    `transito` é saldo próprio (entre depósitos) e não compõe o disponível local.
    """
    with system_conn() as conn:
        sql = (
            "SELECT s.deposito_id, d.nome AS deposito,"
            " s.quantidade AS fisico, s.reserva AS reservado,"
            " COALESCE(s.bloqueado,0) AS bloqueado, COALESCE(s.separacao,0) AS separacao,"
            " COALESCE(s.transito,0) AS transito,"
            " (s.quantidade - s.reserva - COALESCE(s.bloqueado,0) - COALESCE(s.separacao,0)) AS disponivel,"
            " s.localizacao"
            " FROM estoque_saldo s JOIN depositos d ON d.id=s.deposito_id"
            " WHERE s.produto_id=?"
        )
        params: list = [produto_id]
        if deposito_id:
            sql += " AND s.deposito_id=?"
            params.append(deposito_id)
        sql += " ORDER BY d.nome"
        return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]


def saldo_disponivel(produto_id: int, deposito_id: int = 1) -> float:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT (quantidade - reserva - COALESCE(bloqueado,0) - COALESCE(separacao,0)) AS d"
            " FROM estoque_saldo WHERE produto_id=? AND deposito_id=?",
            (produto_id, deposito_id),
        ).fetchone()
    return float(row["d"] or 0) if row else 0.0


# ─── Inventário ───────────────────────────────────────────

def criar_inventario(nome: str, deposito_id: int | None = None) -> int:
    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO inventarios (nome, deposito_id) VALUES (?,?)", (nome.strip(), deposito_id)
        )
        inv_id = cur.lastrowid
        if deposito_id:
            conn.execute(
                "INSERT INTO inventario_itens (inventario_id, produto_id, deposito_id, quantidade_sistema, localizacao)"
                " SELECT ?, produto_id, deposito_id, quantidade, localizacao FROM estoque_saldo WHERE deposito_id=?",
                (inv_id, deposito_id),
            )
        else:
            conn.execute(
                "INSERT INTO inventario_itens (inventario_id, produto_id, deposito_id, quantidade_sistema, localizacao)"
                " SELECT ?, produto_id, deposito_id, quantidade, localizacao FROM estoque_saldo",
                (inv_id,),
            )
        return inv_id


def listar_inventarios() -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT i.*, d.nome AS deposito_nome FROM inventarios i"
            " LEFT JOIN depositos d ON d.id=i.deposito_id ORDER BY i.id DESC"
        ).fetchall()]


def itens_inventario(inventario_id: int) -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT ii.*, p.sku, p.nome AS produto_nome FROM inventario_itens ii"
            " JOIN produtos_cadastro p ON p.id=ii.produto_id"
            " WHERE ii.inventario_id=? ORDER BY p.nome, p.sku",
            (inventario_id,),
        ).fetchall()]


def registrar_contagem(inventario_id: int, item_id: int, contada: float) -> bool:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT quantidade_sistema FROM inventario_itens WHERE id=? AND inventario_id=?",
            (item_id, inventario_id),
        ).fetchone()
        if row is None:
            return False
        divergencia = round(contada - float(row["quantidade_sistema"]), 3)
        conn.execute(
            "UPDATE inventario_itens SET quantidade_contada=?, divergencia=? WHERE id=?",
            (contada, divergencia, item_id),
        )
        return True


def finalizar_inventario(inventario_id: int) -> dict:
    with system_conn() as conn:
        itens = [dict(r) for r in conn.execute(
            "SELECT * FROM inventario_itens WHERE inventario_id=? AND divergencia IS NOT NULL AND divergencia != 0",
            (inventario_id,),
        ).fetchall()]
        ajustados = 0
        for it in itens:
            # movimento de ajuste: baixa/entrada para alinhar ao contado
            conn.execute(
                "UPDATE estoque_saldo SET quantidade=?, atualizado_em=datetime('now')"
                " WHERE produto_id=? AND deposito_id=?",
                (it["quantidade_contada"], it["produto_id"], it["deposito_id"]),
            )
            ajustados += 1
        conn.execute(
            "UPDATE inventarios SET status='finalizado' WHERE id=? AND status='aberto'",
            (inventario_id,),
        )
        return {"ajustados": ajustados, "itens": len(itens)}


# ─── Reposição sugerida ───────────────────────────────────

def reposicao(limit: int = 100) -> list[dict]:
    with system_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT s.produto_id, p.nome, p.sku, p.unidade_venda,"
            " s.quantidade, s.estoque_minimo, s.estoque_maximo,"
            " (SELECT MIN(fp.preco) FROM fornecedor_preco fp WHERE fp.produto_id=p.id AND fp.ativo=1) AS custo"
            " FROM estoque_saldo s"
            " JOIN produtos_cadastro p ON p.id=s.produto_id"
            " WHERE s.estoque_minimo > 0 AND s.quantidade <= s.estoque_minimo"
            " ORDER BY (s.quantidade - s.estoque_minimo) ASC LIMIT ?",
            (limit,),
        ).fetchall()]
        out = []
        for r in rows:
            sugestao = max(0, float(r["estoque_maximo"] or 0) - float(r["quantidade"])) or float(r["estoque_minimo"])
            custo = float(r["custo"] or 0)
            out.append({**r, "sugestao_qtd": round(sugestao, 2),
                        "custo_total": round(sugestao * custo, 2)})
        return out


# ─── Devolução/troca ──────────────────────────────────────

def registrar_devolucao(
    orcamento_id: int,
    produto_id: int,
    quantidade: float,
    motivo: str = "",
    tipo: str = "devolucao",
    deposito_id: int = 1,
    usuario_id: int | None = None,
) -> int:
    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO devolucoes (orcamento_id, produto_id, quantidade, motivo, tipo, deposito_id, usuario_id)"
            " VALUES (?,?,?,?,?,?,?)",
            (orcamento_id, produto_id, quantidade, motivo.strip(), tipo, deposito_id, usuario_id),
        )
        dev_id = cur.lastrowid
        # devolução/troca retorna ao estoque (entrada)
        row = conn.execute(
            "SELECT quantidade FROM estoque_saldo WHERE produto_id=? AND deposito_id=?",
            (produto_id, deposito_id),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE estoque_saldo SET quantidade=quantidade+?, atualizado_em=datetime('now')"
                " WHERE produto_id=? AND deposito_id=?",
                (quantidade, produto_id, deposito_id),
            )
        else:
            conn.execute(
                "INSERT INTO estoque_saldo (produto_id, deposito_id, quantidade) VALUES (?,?,?)",
                (produto_id, deposito_id, quantidade),
            )
        return dev_id


def listar_devolucoes() -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT d.*, p.sku, p.nome AS produto_nome, u.nome AS usuario_nome"
            " FROM devolucoes d"
            " LEFT JOIN produtos_cadastro p ON p.id=d.produto_id"
            " LEFT JOIN usuarios u ON u.id=d.usuario_id ORDER BY d.id DESC"
        ).fetchall()]


def alterar_status_devolucao(devolucao_id: int, status: str) -> bool:
    if status not in ("registrada", "estornada", "trocada"):
        return False
    with system_conn() as conn:
        return conn.execute(
            "UPDATE devolucoes SET status=? WHERE id=?", (status, devolucao_id)
        ).rowcount > 0


# ─── Comissão de vendedores ───────────────────────────────

def comissoes(inicio: str | None = None, fim: str | None = None) -> list[dict]:
    hoje = date.today().isoformat()
    inicio = inicio or (date.today() - timedelta(days=30)).isoformat()
    fim = fim or hoje
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT v.id, v.nome, v.comissao_pct,"
            " COUNT(o.id) AS n_vendas,"
            " COALESCE(SUM(o.total),0) AS total_vendas,"
            " COALESCE(SUM(o.total * v.comissao_pct / 100.0),0) AS comissao"
            " FROM orcamentos o"
            " JOIN clientes c ON c.id=o.cliente_id"
            " JOIN vendedores v ON v.id=c.vendedor_id"
            " WHERE o.status IN ('finalizado','recebido') AND date(o.criado_em) BETWEEN ? AND ?"
            " GROUP BY v.id ORDER BY comissao DESC",
            (inicio, fim),
        ).fetchall()]


# ─── Etiquetas ────────────────────────────────────────────

def dados_etiquetas(produto_ids: list[int]) -> list[dict]:
    produto_ids = list(dict.fromkeys(int(pid) for pid in produto_ids if int(pid) > 0))
    if not produto_ids:
        return []
    ph = ", ".join("?" for _ in produto_ids)
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            f"SELECT p.id, p.sku, p.ean, p.preco, p.nome, p.unidade_venda, p.localizacao"
            f" FROM produtos_cadastro p"
            f" WHERE p.id IN ({ph})",
            produto_ids,
        ).fetchall()]
