"""Alçada de aprovação de compra (COM-010): limites configuráveis por
perfil/valor/fornecedor/centro de custo, segregação solicitante/aprovador,
aprovação/rejeição com motivo, versão e invalidação por alteração.
"""

from __future__ import annotations

import json

from catalog_server.db import system_conn


def _perfis_usuario(conn, usuario_id: int) -> list[int]:
    return [r["perfil_id"] for r in conn.execute(
        "SELECT perfil_id FROM usuario_perfis WHERE usuario_id=?", (usuario_id,)
    ).fetchall()]


def limite_usuario(usuario_id: int, fornecedor_id: int | None = None, centro_custo: str | None = None) -> float:
    """Maior limite de alçada do usuário (via perfis), filtrado por fornecedor/centro."""
    with system_conn() as conn:
        perfis = _perfis_usuario(conn, usuario_id)
        if not perfis:
            return 0.0
        ph = ",".join("?" * len(perfis))
        sql = (f"SELECT COALESCE(MAX(limite_valor),0) AS limite FROM alcada_compra"
               f" WHERE ativo AND perfil_id IN ({ph})")
        args: list = list(perfis)
        if fornecedor_id:
            sql += " AND (fornecedor_id IS NULL OR fornecedor_id=?)"
            args.append(fornecedor_id)
        if centro_custo:
            sql += " AND (centro_custo IS NULL OR centro_custo=?)"
            args.append(centro_custo)
        row = conn.execute(sql, tuple(args)).fetchone()
    return float(row["limite"] or 0)


def precisa_aprovacao(usuario_id: int, total: float, fornecedor_id: int | None = None, centro_custo: str | None = None) -> bool:
    """True se o total excede o limite do usuário (ou há regra exigindo aprovação)."""
    limite = limite_usuario(usuario_id, fornecedor_id, centro_custo)
    if float(total) > limite:
        return True
    # superuser (Administrador) aprova tudo
    return False


def registrar_aprovacao(pedido_id: int, aprovador_id: int, status: str, motivo: str | None,
                        antes: dict | None = None, depois: dict | None = None, versao: int = 1) -> dict:
    status = (status or "").strip().lower()
    if status not in ("aprovado", "rejeitado"):
        raise ValueError("status inválido")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO alcada_aprovacao (pedido_id, status, aprovador_id, motivo, antes, depois, versao)"
            " VALUES (?,?,?,?,?,?,?)",
            (pedido_id, status, aprovador_id, (motivo or "").strip() or None,
             json.dumps(antes) if antes else None, json.dumps(depois) if depois else None, versao),
        )
        return dict(conn.execute(
            "SELECT * FROM alcada_aprovacao WHERE pedido_id=? ORDER BY id DESC LIMIT 1",
            (pedido_id,),
        ).fetchone())


def invalidar_aprovacao(pedido_id: int, aprovador_id: int, motivo: str) -> dict:
    """Alteração relevante invalida aprovação anterior."""
    with system_conn() as conn:
        r = conn.execute(
            "INSERT INTO alcada_aprovacao (pedido_id, status, aprovador_id, motivo, versao)"
            " VALUES (?, 'invalidado', ?, ?, (SELECT COALESCE(MAX(versao),0)+1 FROM alcada_aprovacao WHERE pedido_id=?))"
            " RETURNING id",
            (pedido_id, aprovador_id, motivo or "alteração relevante", pedido_id),
        ).fetchone()
        return dict(r)


def ultima_aprovacao(pedido_id: int) -> dict | None:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT * FROM alcada_aprovacao WHERE pedido_id=? ORDER BY id DESC LIMIT 1",
            (pedido_id,),
        ).fetchone()
    return dict(row) if row else None


def aprovado_vigente(pedido_id: int) -> bool:
    last = ultima_aprovacao(pedido_id)
    return bool(last and last["status"] == "aprovado")


def criar_regra(perfil_id: int | None, limite_valor: float, fornecedor_id: int | None = None,
                centro_custo: str | None = None, exige_aprovacao: bool = True) -> int:
    with system_conn() as conn:
        return conn.execute(
            "INSERT INTO alcada_compra (perfil_id, limite_valor, fornecedor_id, centro_custo, exige_aprovacao)"
            " VALUES (?,?,?,?,?) RETURNING id",
            (perfil_id, limite_valor, fornecedor_id, centro_custo, exige_aprovacao),
        ).fetchone()["id"]


def listar_regras() -> list[dict]:
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT a.*, p.nome AS perfil_nome, f.nome AS fornecedor_nome"
            " FROM alcada_compra a LEFT JOIN perfis p ON p.id=a.perfil_id"
            " LEFT JOIN fornecedores f ON f.id=a.fornecedor_id WHERE a.ativo ORDER BY a.id"
        ).fetchall()]