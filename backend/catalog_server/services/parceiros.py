"""Rede de parceiros profissionais, indicações e fidelização.

Pontos e bônus são append-only; saldos são sempre derivados do ledger.
"""
from __future__ import annotations

import secrets
from math import floor

from catalog_server.db import system_conn


def _codigo(prefixo: str) -> str:
    return f"{prefixo}-{secrets.token_hex(5).upper()}"


def _nome_exibicao(pp: dict) -> str:
    """Nome de exibição do parceiro: apelido > nome > cliente vinculado."""
    return (pp.get("apelido") or pp.get("nome") or pp.get("cliente_nome") or "").strip() or "Parceiro"


def criar(
    categoria: str,
    usuario_id: int | None = None,
    observacao: str | None = None,
    cliente_id: int | None = None,
    nome: str | None = None,
    apelido: str | None = None,
    cpf: str | None = None,
    telefone: str | None = None,
    whatsapp: str | None = None,
    email: str | None = None,
) -> dict:
    categoria = (categoria or "outro").strip().lower()
    categorias = {"eletricista", "encanador", "instalador", "construtor", "arquiteto", "engenheiro", "revenda", "outro"}
    if categoria not in categorias:
        raise ValueError("categoria de parceiro inválida")
    nome = (nome or "").strip()
    apelido = (apelido or "").strip()
    cpf = "".join(c for c in (cpf or "") if c.isdigit())
    with system_conn() as conn:
        if cliente_id:
            cliente = conn.execute("SELECT id, nome FROM clientes WHERE id=?", (cliente_id,)).fetchone()
            if not cliente:
                raise LookupError("Cliente não encontrado")
            existente = conn.execute("SELECT * FROM parceiro_profissional WHERE cliente_id=?", (cliente_id,)).fetchone()
            if existente:
                return {**dict(existente), "duplicado": True}
        elif not nome:
            raise ValueError("Informe o nome completo do parceiro")
        else:
            if cpf:
                existente = conn.execute(
                    "SELECT * FROM parceiro_profissional WHERE cpf=?", (cpf,)
                ).fetchone()
                if existente:
                    return {**dict(existente), "duplicado": True}
            existente = conn.execute(
                "SELECT * FROM parceiro_profissional WHERE nome IS NOT NULL "
                "AND LOWER(nome)=LOWER(?) AND LOWER(COALESCE(apelido,''))=LOWER(?)",
                (nome, apelido),
            ).fetchone()
            if existente:
                return {**dict(existente), "duplicado": True}
        row = conn.execute(
            "INSERT INTO parceiro_profissional "
            "(cliente_id, codigo, categoria, observacao, criado_por, nome, apelido, cpf, telefone, whatsapp, email) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING *",
            (
                cliente_id,
                _codigo("PAR"),
                categoria,
                (observacao or "").strip() or None,
                usuario_id,
                nome or None,
                apelido or None,
                cpf or None,
                (telefone or "").strip() or None,
                (whatsapp or "").strip() or None,
                (email or "").strip() or None,
            ),
        ).fetchone()
        resultado = dict(row)
        resultado["cliente_nome"] = cliente["nome"] if cliente_id else (nome or "")
        resultado["duplicado"] = False
        return resultado


def alterar_status(parceiro_id: int, status: str, usuario_id: int | None = None) -> dict:
    status = (status or "").strip().lower()
    if status not in {"pendente", "ativo", "suspenso", "bloqueado", "inativo"}:
        raise ValueError("status de parceiro inválido")
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM parceiro_profissional WHERE id=? FOR UPDATE", (parceiro_id,)).fetchone()
        if not row:
            raise LookupError("Parceiro não encontrado")
        conn.execute(
            "UPDATE parceiro_profissional SET status=?, atualizado_em=NOW(), "
            "aprovado_por=CASE WHEN ?='ativo' THEN ? ELSE aprovado_por END, "
            "aprovado_em=CASE WHEN ?='ativo' THEN NOW() ELSE aprovado_em END, "
            "bloqueado_por=CASE WHEN ? IN ('bloqueado','suspenso') THEN ? ELSE bloqueado_por END, "
            "bloqueado_em=CASE WHEN ? IN ('bloqueado','suspenso') THEN NOW() ELSE bloqueado_em END WHERE id=?",
            (status, status, usuario_id, status, status, usuario_id, status, parceiro_id),
        )
    return {"id": parceiro_id, "status": status}


def listar(status: str | None = None, categoria: str | None = None, termo: str | None = None) -> list[dict]:
    sql = ("SELECT pp.*, COALESCE(c.nome, pp.nome, '') AS cliente_nome, "
           "COALESCE(c.doc, pp.cpf, '') AS cliente_doc FROM parceiro_profissional pp "
           "LEFT JOIN clientes c ON c.id=pp.cliente_id WHERE 1=1")
    args: list = []
    if status:
        sql += " AND pp.status=?"
        args.append(status)
    if categoria:
        sql += " AND pp.categoria=?"
        args.append(categoria)
    if termo:
        sql += (" AND (COALESCE(c.nome, pp.nome, '') ILIKE ? OR COALESCE(pp.apelido, '') ILIKE ? "
                "OR COALESCE(pp.cpf, c.doc, '') ILIKE ? OR pp.codigo ILIKE ?)")
        args.extend([f"%{termo}%"] * 4)
    sql += " ORDER BY pp.id DESC LIMIT 500"
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]


def listar_ativos_indicacao() -> list[dict]:
    """Parceiros ativos para o seletor de indicação no PDV (campos mínimos).

    O operador do caixa só precisa identificar o parceiro que indicou; os
    dados financeiros da rede ficam restritos a Administrador/Financeiro.
    """
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT pp.id, pp.apelido, pp.nome, COALESCE(c.nome,'') AS cliente_nome, pp.codigo "
            "FROM parceiro_profissional pp LEFT JOIN clientes c ON c.id=pp.cliente_id "
            "WHERE pp.status='ativo' ORDER BY COALESCE(pp.apelido, pp.nome, c.nome, pp.codigo) LIMIT 500"
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["nome_exibicao"] = _nome_exibicao(d)
            out.append(d)
        return out


def criar_indicacao(parceiro_id: int, cliente_id: int | None = None) -> dict:
    with system_conn() as conn:
        parceiro = conn.execute("SELECT id, status FROM parceiro_profissional WHERE id=?", (parceiro_id,)).fetchone()
        if not parceiro:
            raise LookupError("Parceiro não encontrado")
        if parceiro["status"] != "ativo":
            raise ValueError("Somente parceiro ativo pode indicar")
        row = conn.execute(
            "INSERT INTO parceiro_indicacao (parceiro_id, codigo, cliente_id) VALUES (?,?,?) RETURNING *",
            (parceiro_id, _codigo("IND"), cliente_id),
        ).fetchone()
        return dict(row)


def _converter_indicacao(conn, indicacao_id: int, orcamento_id: int, usuario_id: int | None = None) -> dict:
        indicacao = conn.execute("SELECT * FROM parceiro_indicacao WHERE id=? FOR UPDATE", (indicacao_id,)).fetchone()
        if not indicacao:
            raise LookupError("Indicação não encontrada")
        if indicacao["status"] != "registrada":
            raise ValueError("Indicação já processada")
        venda = conn.execute("SELECT * FROM orcamentos WHERE id=?", (orcamento_id,)).fetchone()
        if not venda or venda["status"] not in ("finalizado", "recebido"):
            raise ValueError("Indicação só pode ser convertida em venda concluída")
        if indicacao["cliente_id"] and indicacao["cliente_id"] != venda["cliente_id"]:
            raise ValueError("A indicação pertence a outro cliente")
        politica = conn.execute(
            "SELECT percentual_bonus, pontos_por_real FROM parceiro_politica "
            "WHERE categoria=(SELECT categoria FROM parceiro_profissional WHERE id=?) AND ativo "
            "ORDER BY versao DESC LIMIT 1",
            (indicacao["parceiro_id"],),
        ).fetchone() or conn.execute(
            "SELECT percentual_bonus, pontos_por_real FROM parceiro_politica "
            "WHERE categoria='outro' AND ativo ORDER BY versao DESC LIMIT 1"
        ).fetchone()
        if politica is None:
            # O bootstrap de testes limpa tabelas após aplicar migrations; em
            # ambiente normal a 0146 sempre cria esta política no banco.
            politica = {"percentual_bonus": 1, "pontos_por_real": 1}
        valor_venda = float(venda["total_liquido"] or venda["total"] or 0)
        bonus = round(valor_venda * float(politica["percentual_bonus"] or 0) / 100, 2)
        pontos = floor(valor_venda * float(politica["pontos_por_real"] or 0))
        conn.execute(
            "UPDATE parceiro_indicacao SET status='convertida', orcamento_id=?, convertido_em=NOW() WHERE id=?",
            (orcamento_id, indicacao_id),
        )
        bonus_id = None
        if bonus > 0:
            bonus_id = conn.execute(
                "INSERT INTO parceiro_bonus (parceiro_id, indicacao_id, orcamento_id, valor, motivo) "
                "VALUES (?,?,?,?,?) RETURNING id",
                (indicacao["parceiro_id"], indicacao_id, orcamento_id, bonus, "Indicação convertida"),
            ).fetchone()["id"]
        ponto_id = None
        if pontos > 0:
            ponto_id = conn.execute(
                "INSERT INTO parceiro_ponto (parceiro_id, tipo, pontos, origem_tipo, origem_id, idempotency_key, observacao, usuario_id) "
                "VALUES (?,?,?,?,?,?,?,?) RETURNING id",
                (indicacao["parceiro_id"], "credito", pontos, "venda_indicada", orcamento_id,
                 f"indicacao-{indicacao_id}", "Pontos por venda indicada", usuario_id),
            ).fetchone()["id"]
        return {"indicacao_id": indicacao_id, "orcamento_id": orcamento_id, "bonus_id": bonus_id,
                "bonus": bonus, "pontos_id": ponto_id, "pontos": pontos}


def converter_indicacao(indicacao_id: int, orcamento_id: int, usuario_id: int | None = None, _conn=None) -> dict:
    if _conn is not None:
        return _converter_indicacao(_conn, indicacao_id, orcamento_id, usuario_id)
    with system_conn() as conn:
        return _converter_indicacao(conn, indicacao_id, orcamento_id, usuario_id)


def validar_indicacao(indicacao_id: int, cliente_id: int | None, _conn=None) -> None:
    def _validar(conn) -> None:
        row = conn.execute(
            "SELECT i.status, i.cliente_id, p.status AS parceiro_status "
            "FROM parceiro_indicacao i JOIN parceiro_profissional p ON p.id=i.parceiro_id "
            "WHERE i.id=?",
            (indicacao_id,),
        ).fetchone()
        if not row:
            raise LookupError("Indicação não encontrada")
        if row["status"] != "registrada":
            raise ValueError("Indicação já processada")
        if row["parceiro_status"] != "ativo":
            raise ValueError("Indicação de parceiro inativo não pode ser vinculada")
        if row["cliente_id"] and row["cliente_id"] != cliente_id:
            raise ValueError("A indicação pertence a outro cliente")

    if _conn is not None:
        _validar(_conn)
    else:
        with system_conn() as conn:
            _validar(conn)


def aprovar_bonus(bonus_id: int, usuario_id: int | None = None) -> dict:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE parceiro_bonus SET status='aprovado', aprovado_por=?, aprovado_em=NOW() "
            "WHERE id=? AND status='pendente' RETURNING id",
            (usuario_id, bonus_id),
        ).fetchone()
        if not cur:
            raise ValueError("Bônus inexistente ou fora da fila de aprovação")
    return {"id": bonus_id, "status": "aprovado"}


def pagar_bonus(bonus_id: int, usuario_id: int | None = None) -> dict:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE parceiro_bonus SET status='pago', pago_por=?, pago_em=NOW() "
            "WHERE id=? AND status='aprovado' RETURNING id",
            (usuario_id, bonus_id),
        ).fetchone()
        if not cur:
            raise ValueError("Bônus inexistente ou ainda não aprovado")
    return {"id": bonus_id, "status": "pago"}


def ledger(parceiro_id: int) -> dict:
    with system_conn() as conn:
        parceiro = conn.execute(
            "SELECT pp.*, COALESCE(c.nome, pp.nome, '') AS cliente_nome, COALESCE(c.doc, pp.cpf, '') AS cliente_doc "
            "FROM parceiro_profissional pp LEFT JOIN clientes c ON c.id=pp.cliente_id WHERE pp.id=?",
            (parceiro_id,),
        ).fetchone()
        if not parceiro:
            raise LookupError("Parceiro não encontrado")
        p = dict(parceiro)
        p["nome_exibicao"] = _nome_exibicao(p)
        pontos = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='credito' OR tipo='ajuste' THEN pontos ELSE -pontos END),0) saldo "
            "FROM parceiro_ponto WHERE parceiro_id=?", (parceiro_id,)
        ).fetchone()
        itens = [dict(r) for r in conn.execute(
            "SELECT * FROM parceiro_ponto WHERE parceiro_id=? ORDER BY id DESC LIMIT 200", (parceiro_id,)
        ).fetchall()]
        bonus = [dict(r) for r in conn.execute(
            "SELECT * FROM parceiro_bonus WHERE parceiro_id=? ORDER BY id DESC LIMIT 200", (parceiro_id,)
        ).fetchall()]
        vendas = [dict(r) for r in conn.execute(
            "SELECT o.id AS orcamento_id, o.numero, o.total_liquido AS total, o.criado_em, "
            " COALESCE(cl.nome, 'Consumidor') AS cliente_nome, i.codigo AS indicacao_codigo "
            "FROM parceiro_indicacao i "
            "JOIN orcamentos o ON o.id=i.orcamento_id "
            "LEFT JOIN clientes cl ON cl.id=o.cliente_id "
            "WHERE i.parceiro_id=? AND i.status='convertida' "
            "ORDER BY o.criado_em DESC LIMIT 200",
            (parceiro_id,),
        ).fetchall()]
    return {
        "parceiro_id": parceiro_id,
        "parceiro": p,
        "saldo_pontos": float(pontos["saldo"] or 0),
        "pontos": itens,
        "bonus": bonus,
        "vendas": vendas,
    }
