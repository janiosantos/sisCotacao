from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from catalog_server import auth_token
from catalog_server.db import system_conn
from catalog_server.repositories import usuario_repo

api_usuarios_bp = Blueprint("api_usuarios", __name__)

# Mantido: outros blueprints (orcamentos, fiscal, loja, precos) usam a sessão
# para atribuir o usuário logado às operações.
SESSION_KEY = "usuario_id"


@api_usuarios_bp.get("/api/usuarios")
def listar():
    somente_ativos = request.args.get("somente_ativos", "").lower() in ("1", "true")
    return jsonify(usuario_repo.list(somente_ativos=somente_ativos))


@api_usuarios_bp.get("/api/usuarios/atual")
def usuario_atual():
    payload = getattr(request, "usuario", None)
    if not payload:
        return jsonify({"autenticado": False}), 200
    user = usuario_repo.get(payload["sub"])
    if not user:
        return jsonify({"autenticado": False}), 200
    return jsonify({"autenticado": True, **user})


@api_usuarios_bp.post("/api/usuarios")
def criar():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    login = (data.get("login") or "").strip().lower()
    senha = data.get("senha") or ""
    if not nome or not login or len(senha) < 4:
        return jsonify({"error": "Informe nome, login e senha (mín. 4 caracteres)"}), 400
    if usuario_repo.get_by_login(login):
        return jsonify({"error": "Login já em uso"}), 409
    usuario_id = usuario_repo.create(
        nome,
        login,
        generate_password_hash(senha),
        desconto_limite_pct=float(data.get("desconto_limite_pct") or 0),
        autoriza_desconto=bool(data.get("autoriza_desconto")),
    )
    _sincronizar_rbac(usuario_id, data)
    return jsonify({"id": usuario_id}), 201


def _sincronizar_rbac(usuario_id: int, data: dict) -> None:
    """Mantém a relação RBAC coerente com o cadastro de usuário.

    Usa `perfil_ids` quando informado; senão deriva do hint `perfil` legado
    (admin → Administrador, senão → Vendedor) para o fluxo de primeiro acesso.
    Grava `overrides` (conceder/negar) quando informado.
    """
    from catalog_server import permissao

    perfil_ids = data.get("perfil_ids")
    if perfil_ids:
        permissao.definir_perfis(usuario_id, [int(p) for p in perfil_ids])
    else:
        hint = (data.get("perfil") or "").strip().lower()
        nome_perfil = "Administrador" if hint == "admin" else "Vendedor"
        with system_conn() as conn:
            pid = conn.execute(
                "SELECT id FROM perfis WHERE nome=?", (nome_perfil,)
            ).fetchone()
        if pid:
            permissao.definir_perfis(usuario_id, [pid["id"]])

    conceder = data.get("conceder")
    negar = data.get("negar")
    legado = data.get("overrides")
    if conceder or negar or legado:
        permissao.definir_overrides(usuario_id, legado, conceder=conceder, negar=negar)


@api_usuarios_bp.put("/api/usuarios/<int:usuario_id>")
def atualizar(usuario_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    senha = data.get("senha") or ""
    if not nome:
        return jsonify({"error": "Informe o nome do usuário"}), 400
    senha_hash = generate_password_hash(senha) if len(senha) >= 4 else None
    ok = usuario_repo.update(
        usuario_id,
        nome,
        senha_hash,
        desconto_limite_pct=(
            float(data["desconto_limite_pct"])
            if data.get("desconto_limite_pct") is not None
            else None
        ),
        autoriza_desconto=(
            bool(data["autoriza_desconto"])
            if data.get("autoriza_desconto") is not None
            else None
        ),
    )
    if not ok:
        return jsonify({"error": "Usuário não encontrado"}), 404
    _sincronizar_rbac(usuario_id, data)
    return jsonify({"ok": True})


@api_usuarios_bp.patch("/api/usuarios/<int:usuario_id>/ativo")
def alternar_ativo(usuario_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    ok = usuario_repo.set_ativo(usuario_id, ativo)
    if not ok:
        return jsonify({"error": "Usuário não encontrado"}), 404
    return jsonify({"ok": True})


@api_usuarios_bp.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    login_str = (data.get("login") or "").strip().lower()
    senha = data.get("senha") or ""
    user = usuario_repo.get_by_login(login_str)
    if not user or not check_password_hash(user["senha_hash"], senha) or not user.get("ativo"):
        return jsonify({"error": "Usuário ou senha inválidos"}), 401
    session[SESSION_KEY] = user["id"]
    token = auth_token.criar_token(user)
    atual = usuario_repo.get(user["id"]) or user
    return jsonify(
        {
            "autenticado": True,
            "token": token,
            "id": atual["id"],
            "nome": atual["nome"],
            "login": atual["login"],
            "desconto_limite_pct": atual.get("desconto_limite_pct") or 0,
            "autoriza_desconto": bool(atual.get("autoriza_desconto")),
            "perfil_ids": atual.get("perfil_ids") or [],
            "overrides": atual.get("overrides") or {},
            "permissoes": atual.get("permissoes") or [],
        }
    )


@api_usuarios_bp.post("/api/logout")
def logout():
    return jsonify({"ok": True})


@api_usuarios_bp.get("/api/primeiro-usuario")
def existe_usuario():
    """True quando ainda não há usuários cadastrados (para o fluxo de setup inicial)."""
    return jsonify({"vazio": usuario_repo.count() == 0})
