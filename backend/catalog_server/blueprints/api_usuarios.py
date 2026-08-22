from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from catalog_server import auth_token
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
    perfil = data.get("perfil") or "vendedor"
    if not nome or not login or len(senha) < 4:
        return jsonify({"error": "Informe nome, login e senha (mín. 4 caracteres)"}), 400
    if perfil not in usuario_repo.PERFIS:
        return jsonify({"error": "Perfil inválido"}), 400
    if usuario_repo.get_by_login(login):
        return jsonify({"error": "Login já em uso"}), 409
    usuario_id = usuario_repo.create(
        nome,
        login,
        generate_password_hash(senha),
        perfil,
        desconto_limite_pct=float(data.get("desconto_limite_pct") or 0),
        autoriza_desconto=bool(data.get("autoriza_desconto")),
    )
    return jsonify({"id": usuario_id}), 201


@api_usuarios_bp.put("/api/usuarios/<int:usuario_id>")
def atualizar(usuario_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    perfil = data.get("perfil") or "vendedor"
    senha = data.get("senha") or ""
    if not nome:
        return jsonify({"error": "Informe o nome do usuário"}), 400
    if perfil not in usuario_repo.PERFIS:
        return jsonify({"error": "Perfil inválido"}), 400
    senha_hash = generate_password_hash(senha) if len(senha) >= 4 else None
    ok = usuario_repo.update(
        usuario_id,
        nome,
        perfil,
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
    return jsonify(
        {
            "autenticado": True,
            "token": token,
            "id": user["id"],
            "nome": user["nome"],
            "login": user["login"],
            "perfil": user["perfil"],
        }
    )


@api_usuarios_bp.post("/api/logout")
def logout():
    return jsonify({"ok": True})


@api_usuarios_bp.get("/api/primeiro-usuario")
def existe_usuario():
    """True quando ainda não há usuários cadastrados (para o fluxo de setup inicial)."""
    return jsonify({"vazio": usuario_repo.count() == 0})
