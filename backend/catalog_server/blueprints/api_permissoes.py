"""API do controle de acesso por perfil (RBAC, migração 0075).

- GET /api/perfis                    perfis com matriz de permissões
- PUT /api/perfis/<id>/permissoes    grava a matriz de um perfil
- GET /api/permissoes/catalogo       catálogo de recursos/ações (para a UI)
- PUT /api/usuarios/<id>/perfis      define os perfis de um usuário
- PUT /api/usuarios/<id>/overrides   concede ou nega ações extras por tela
"""
from __future__ import annotations

import json

from flask import Blueprint, abort, jsonify, request

from catalog_server import permissao
from catalog_server.db import system_conn

api_permissoes_bp = Blueprint("api_permissoes", __name__)


def _actor_id() -> int | None:
    payload = getattr(request, "usuario", None)
    return int(payload["sub"]) if payload and payload.get("sub") else None


def _recursos(conn) -> dict[int, dict]:
    rows = conn.execute(
        "SELECT id, codigo, nome, grupo FROM recursos ORDER BY grupo, nome"
    ).fetchall()
    return {int(r["id"]): dict(r) for r in rows}


@api_permissoes_bp.get("/api/perfis")
def listar_perfis():
    with system_conn() as conn:
        perfis_rows = conn.execute(
            "SELECT id, nome, descricao, ativo FROM perfis ORDER BY nome"
        ).fetchall()
        recursos = _recursos(conn)
        perfil_acoes: dict[int, dict[int, list[str]]] = {}
        for r in conn.execute(
            "SELECT perfil_id, recurso_id, acoes FROM perfil_recurso"
        ).fetchall():
            perfil_acoes.setdefault(int(r["perfil_id"]), {})[int(r["recurso_id"])] = _parse_acoes(r["acoes"])

    out = []
    for p in perfis_rows:
        pid = int(p["id"])
        matriz = {
            recursos[rid]["codigo"]: acoes
            for rid, acoes in perfil_acoes.get(pid, {}).items()
            if rid in recursos
        }
        out.append({
            "id": pid,
            "nome": p["nome"],
            "descricao": p["descricao"],
            "ativo": bool(p["ativo"]),
            "permissoes": matriz,
            "superuser": p["nome"] == "Administrador",
        })
    return jsonify(out)


@api_permissoes_bp.post("/api/perfis")
def criar_perfil():
    data = request.get_json(silent=True) or {}
    matriz = data.get("permissoes")
    if matriz is not None:
        try:
            _validar_matriz(matriz)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    try:
        pid = permissao.criar_perfil(
            data.get("nome") or "", data.get("descricao") or "",
            actor_id=_actor_id(), ip=request.remote_addr,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if matriz:
        try:
            _aplicar_matriz(
                pid, matriz, actor_id=_actor_id(), ip=request.remote_addr
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    return jsonify({"id": pid}), 201


@api_permissoes_bp.put("/api/perfis/<int:perfil_id>")
def atualizar_perfil(perfil_id: int):
    data = request.get_json(silent=True) or {}
    try:
        ok = permissao.atualizar_perfil(
            perfil_id, data.get("nome") or "", data.get("descricao") or "",
            actor_id=_actor_id(), ip=request.remote_addr,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ok:
        return jsonify({"error": "Perfil não encontrado"}), 404
    return jsonify({"ok": True})


@api_permissoes_bp.patch("/api/perfis/<int:perfil_id>/ativo")
def alternar_ativo_perfil(perfil_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    try:
        ok = permissao.set_perfil_ativo(
            perfil_id, ativo, actor_id=_actor_id(), ip=request.remote_addr
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ok:
        return jsonify({"error": "Perfil não encontrado"}), 404
    return jsonify({"ok": True})


@api_permissoes_bp.delete("/api/perfis/<int:perfil_id>")
def excluir_perfil(perfil_id: int):
    try:
        ok = permissao.excluir_perfil(
            perfil_id, actor_id=_actor_id(), ip=request.remote_addr
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ok:
        return jsonify({"error": "Perfil não encontrado"}), 404
    return jsonify({"ok": True})


def _aplicar_matriz(
    perfil_id: int,
    matriz: dict,
    *,
    actor_id: int | None = None,
    ip: str | None = None,
) -> None:
    """Persiste a matriz recurso→ações de um perfil (após criar/atualizar)."""
    _validar_matriz(matriz)
    with system_conn() as conn:
        recursos = {r["codigo"]: int(r["id"]) for r in conn.execute(
            "SELECT id, codigo FROM recursos"
        ).fetchall()}
        antes = [dict(row) for row in conn.execute(
            "SELECT r.codigo, pr.acoes FROM perfil_recurso pr "
            "JOIN recursos r ON r.id=pr.recurso_id WHERE pr.perfil_id=? ORDER BY r.codigo",
            (perfil_id,),
        ).fetchall()]
        conn.execute("DELETE FROM perfil_recurso WHERE perfil_id=?", (perfil_id,))
        for codigo, acoes in matriz.items():
            rid = recursos.get(str(codigo))
            if rid is None:
                raise ValueError(f"Recurso inválido: {codigo}")
            if not isinstance(acoes, list):
                raise ValueError(f"Ações inválidas para o recurso: {codigo}")
            desconhecidas = [a for a in acoes if a not in permissao.ACOES]
            if desconhecidas:
                raise ValueError(f"Ação inválida: {desconhecidas[0]}")
            validas = list(dict.fromkeys(acoes))
            if not validas:
                continue
            conn.execute(
                "INSERT INTO perfil_recurso (perfil_id, recurso_id, acoes)"
                " VALUES (?,?,?)",
                (perfil_id, rid, json.dumps(validas)),
            )
        depois = [dict(row) for row in conn.execute(
            "SELECT r.codigo, pr.acoes FROM perfil_recurso pr "
            "JOIN recursos r ON r.id=pr.recurso_id WHERE pr.perfil_id=? ORDER BY r.codigo",
            (perfil_id,),
        ).fetchall()]
        permissao._registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=None,
            target_perfil_id=perfil_id, operacao="gravar_permissoes",
            recurso="perfis", antes=antes, depois=depois, ip=ip,
        )
        conn.commit()
        permissao.invalidar()


def _validar_matriz(matriz: dict) -> None:
    if not isinstance(matriz, dict):
        raise ValueError("permissoes deve ser um objeto recurso -> ações")
    with system_conn() as conn:
        recursos = {r["codigo"] for r in conn.execute("SELECT codigo FROM recursos")}
    for codigo, acoes in matriz.items():
        if str(codigo) not in recursos:
            raise ValueError(f"Recurso inválido: {codigo}")
        if not isinstance(acoes, list):
            raise ValueError(f"Ações inválidas para o recurso: {codigo}")
        desconhecidas = [a for a in acoes if a not in permissao.ACOES]
        if desconhecidas:
            raise ValueError(f"Ação inválida: {desconhecidas[0]}")


@api_permissoes_bp.put("/api/perfis/<int:perfil_id>/permissoes")
def gravar_permissoes(perfil_id: int):
    data = request.get_json(silent=True) or {}
    matriz = data.get("permissoes") or {}
    if not isinstance(matriz, dict):
        return jsonify({"error": "permissoes deve ser um objeto recurso -> [ações]"}), 400
    with system_conn() as conn:
        p = conn.execute(
            "SELECT id, nome FROM perfis WHERE id=?", (perfil_id,)
        ).fetchone()
        if p is None:
            return jsonify({"error": "Perfil não encontrado"}), 404
        if p["nome"] == "Administrador":
            return jsonify({"error": "O perfil Administrador é superuser (não usa matriz)"}), 400
    try:
        _aplicar_matriz(
            perfil_id, matriz, actor_id=_actor_id(), ip=request.remote_addr
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_permissoes_bp.get("/api/permissoes/catalogo")
def catalogo():
    with system_conn() as conn:
        recursos = [
            dict(r) for r in conn.execute(
                "SELECT codigo, nome, grupo FROM recursos"
                " WHERE ativo=1 ORDER BY grupo, nome"
            ).fetchall()
        ]
    return jsonify({
        "recursos": recursos,
        "acoes": list(permissao.ACOES),
    })


@api_permissoes_bp.put("/api/usuarios/<int:usuario_id>/perfis")
def definir_perfis(usuario_id: int):
    data = request.get_json(silent=True) or {}
    perfil_ids = data.get("perfil_ids") or []
    if not isinstance(perfil_ids, list):
        return jsonify({"error": "perfil_ids deve ser uma lista"}), 400
    with system_conn() as conn:
        if conn.execute(
            "SELECT 1 FROM usuarios WHERE id=?", (usuario_id,)
        ).fetchone() is None:
            return jsonify({"error": "Usuário não encontrado"}), 404
    try:
        permissao.definir_perfis(
            usuario_id, [int(p) for p in perfil_ids],
            actor_id=_actor_id(), ip=request.remote_addr,
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_permissoes_bp.put("/api/usuarios/<int:usuario_id>/overrides")
def definir_overrides(usuario_id: int):
    data = request.get_json(silent=True) or {}
    conceder = data.get("conceder")
    negar = data.get("negar")
    legado = data.get("overrides")
    if conceder is None and negar is None and legado is None:
        return jsonify({"error": "Informe conceder/negar (ou overrides legado)"}), 400
    if legado is not None and not isinstance(legado, dict):
        return jsonify({"error": "overrides deve ser um objeto recurso -> [ações]"}), 400
    if conceder is not None and not isinstance(conceder, dict):
        return jsonify({"error": "conceder deve ser um objeto recurso -> [ações]"}), 400
    if negar is not None and not isinstance(negar, dict):
        return jsonify({"error": "negar deve ser um objeto recurso -> [ações]"}), 400
    with system_conn() as conn:
        if conn.execute(
            "SELECT 1 FROM usuarios WHERE id=?", (usuario_id,)
        ).fetchone() is None:
            return jsonify({"error": "Usuário não encontrado"}), 404
    try:
        permissao.definir_overrides(
            usuario_id, legado, conceder=conceder, negar=negar,
            actor_id=_actor_id(), ip=request.remote_addr,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_permissoes_bp.get("/api/perfis/auditoria")
def auditoria():
    return jsonify(permissao.listar_auditoria(
        limite=request.args.get("limite", type=int) or 200,
        usuario_id=request.args.get("usuario_id", type=int),
    ))


def _parse_acoes(valor) -> list[str]:
    if isinstance(valor, list):
        return [a for a in valor if a in permissao.ACOES]
    try:
        lista = json.loads(valor) if isinstance(valor, str) else []
    except (TypeError, ValueError):
        lista = []
    return [a for a in lista if a in permissao.ACOES]


def permissoes_efetivas(usuario_id: int) -> list[str]:
    """Lista achatada `recurso.acao` das permissões efetivas do usuário."""
    from catalog_server import permissao as _p

    if not usuario_id:
        return []
    acoes = _p._carregar(usuario_id)  # dict recurso -> set(acao)
    if "__superuser__" in acoes:
        # Admin: devolve todas as combinações possíveis.
        from catalog_server.db import system_conn as _sc

        combs: list[str] = []
        with _sc() as conn:
            for r in conn.execute("SELECT codigo FROM recursos WHERE ativo=1").fetchall():
                for a in _p.ACOES:
                    combs.append(f"{r['codigo']}.{a}")
        return combs
    return [f"{recurso}.{acao}" for recurso, conjunto in acoes.items() for acao in sorted(conjunto)]


def perfil_ids_usuario(usuario_id: int) -> list[int]:
    with system_conn() as conn:
        return [int(r["perfil_id"]) for r in conn.execute(
            "SELECT perfil_id FROM usuario_perfis WHERE usuario_id=?", (usuario_id,)
        ).fetchall()]


def overrides_usuario(usuario_id: int) -> dict:
    """Overrides do usuário: `{recurso: {conceder: [...], negar: [...]}}`.

    Mantém compatibilidade com o formato antigo `{recurso: [ações]}` (só
    conceder) para não quebrar consumidores antigos.
    """
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.codigo AS codigo, uo.acoes_extra, uo.acoes_negadas
            FROM usuario_override uo JOIN recursos r ON r.id=uo.recurso_id
            WHERE uo.usuario_id=?
            """,
            (usuario_id,),
        ).fetchall()
    out: dict = {}
    for r in rows:
        conceder = _parse_acoes(r["acoes_extra"])
        negar = _parse_acoes(r["acoes_negadas"]) if r["acoes_negadas"] is not None else []
        if negar:
            out[r["codigo"]] = {"conceder": conceder, "negar": negar}
        else:
            out[r["codigo"]] = conceder  # formato legado (compat)
    return out
