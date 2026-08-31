from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from catalog_server import auth_token, config
from catalog_server.db import system_conn
from catalog_server.repositories import usuario_repo

api_usuarios_bp = Blueprint("api_usuarios", __name__)

# Mantido: outros blueprints (orcamentos, fiscal, loja, precos) usam a sessão
# para atribuir o usuário logado às operações.
SESSION_KEY = "usuario_id"


def usuario_id_requisicao() -> int | None:
    """Identidade da requisição validada pelo Bearer, com fallback legado."""
    payload = getattr(request, "usuario", None)
    if payload and payload.get("sub"):
        return int(payload["sub"])
    valor = session.get(SESSION_KEY)
    return int(valor) if valor else None


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
    primeiro_acesso = not usuario_repo.count()
    if primeiro_acesso:
        # O lock e a rechecagem precisam ocorrer na mesma conexão do INSERT;
        # duas requisições simultâneas não podem criar dois administradores.
        with system_conn() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(804272)")
            if conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
                return jsonify({"error": "Primeiro usuário já foi criado"}), 409
            cur = conn.execute(
                "INSERT INTO usuarios (nome, login, senha_hash, desconto_limite_pct, autoriza_desconto)"
                " VALUES (?,?,?,?,?)",
                (
                    nome,
                    login,
                    generate_password_hash(senha),
                    float(data.get("desconto_limite_pct") or 0),
                    bool(data.get("autoriza_desconto")),
                ),
            )
            usuario_id = int(cur.lastrowid)
        bootstrap_data = {
            key: value for key, value in data.items()
            if key not in ("perfil", "perfil_ids")
        }
        _sincronizar_rbac(
            usuario_id, {**bootstrap_data, "perfil": "admin"}, actor_id=None
        )
        return jsonify({"id": usuario_id}), 201
    if usuario_repo.get_by_login(login):
        return jsonify({"error": "Login já em uso"}), 409
    from catalog_server import permissao

    try:
        _validar_payload_rbac(data, permissao, usuario_id_requisicao())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    usuario_id = usuario_repo.create(
        nome,
        login,
        generate_password_hash(senha),
        desconto_limite_pct=float(data.get("desconto_limite_pct") or 0),
        autoriza_desconto=bool(data.get("autoriza_desconto")),
    )
    try:
        _sincronizar_rbac(usuario_id, data, actor_id=usuario_id_requisicao())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": usuario_id}), 201


def _sincronizar_rbac(
    usuario_id: int,
    data: dict,
    *,
    actor_id: int | None = None,
) -> None:
    """Mantém a relação RBAC coerente com o cadastro de usuário.

    Usa `perfil_ids` quando informado; senão deriva do hint `perfil` legado
    (admin → Administrador, senão → Vendedor) para o fluxo de primeiro acesso.
    Grava `overrides` (conceder/negar) quando informado.
    """
    from catalog_server import permissao

    perfil_ids = data.get("perfil_ids")
    if "perfil_ids" in data:
        permissao.definir_perfis(
            usuario_id, perfil_ids, actor_id=actor_id, ip=request.remote_addr
        )
    else:
        hint = (data.get("perfil") or "").strip().lower()
        nome_perfil = "Administrador" if hint == "admin" else "Vendedor"
        with system_conn() as conn:
            pid = conn.execute(
                "SELECT id FROM perfis WHERE nome=?", (nome_perfil,)
            ).fetchone()
        if pid:
            permissao.definir_perfis(
                usuario_id, [pid["id"]], actor_id=actor_id, ip=request.remote_addr
            )

    conceder = data.get("conceder")
    negar = data.get("negar")
    legado = data.get("overrides")
    if "conceder" in data or "negar" in data or "overrides" in data:
        permissao.definir_overrides(
            usuario_id, legado, conceder=conceder, negar=negar,
            actor_id=actor_id, ip=request.remote_addr,
        )


def _validar_payload_rbac(data: dict, permissao, actor_id: int | None) -> None:
    """Valida RBAC antes de persistir os campos escalares do usuário."""
    if "perfil_ids" in data:
        permissao.validar_perfil_ids(data["perfil_ids"], actor_id=actor_id)
    if "conceder" in data or "negar" in data or "overrides" in data:
        permissao.validar_overrides_payload(
            data.get("conceder"), data.get("negar"), overrides=data.get("overrides")
        )


@api_usuarios_bp.put("/api/usuarios/<int:usuario_id>")
def atualizar(usuario_id: int):
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    senha = data.get("senha") or ""
    if not nome:
        return jsonify({"error": "Informe o nome do usuário"}), 400
    from catalog_server import permissao

    try:
        _validar_payload_rbac(data, permissao, usuario_id_requisicao())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
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
    try:
        _sincronizar_rbac(usuario_id, data, actor_id=usuario_id_requisicao())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@api_usuarios_bp.patch("/api/usuarios/<int:usuario_id>/ativo")
def alternar_ativo(usuario_id: int):
    ativo = request.args.get("ativo", "").lower() in ("1", "true")
    from catalog_server import permissao

    actor_id = usuario_id_requisicao()
    try:
        ok = permissao.alterar_ativo(
            actor_id, usuario_id, ativo, ip=request.remote_addr
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ok:
        return jsonify({"error": "Usuário não encontrado"}), 404
    return jsonify({"ok": True})


@api_usuarios_bp.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    login_str = (data.get("login") or "").strip().lower()
    senha = data.get("senha") or ""
    from catalog_server.services import login_rate_limit

    ip = request.remote_addr or "unknown"
    if not login_rate_limit.permitir(ip, login_str):
        resposta = jsonify({"error": "Muitas tentativas. Tente novamente mais tarde."})
        resposta.headers["Retry-After"] = str(config.LOGIN_RATE_WINDOW_SECONDS)
        return resposta, 429
    user = usuario_repo.get_by_login(login_str)
    if not user or not check_password_hash(user["senha_hash"], senha) or not user.get("ativo"):
        return jsonify({"error": "Usuário ou senha inválidos"}), 401
    login_rate_limit.limpar(ip, login_str)
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
    payload = auth_token.validar_token(
        request.headers.get("Authorization", "")[7:]
        if request.headers.get("Authorization", "").startswith("Bearer ")
        else None
    )
    if payload and payload.get("sub"):
        with system_conn() as conn:
            conn.execute(
                "UPDATE usuarios SET token_version=token_version+1, "
                "atualizado_em=datetime('now') WHERE id=?",
                (payload["sub"],),
            )
        from catalog_server import permissao

        permissao.invalidar(int(payload["sub"]))
    session.clear()
    return jsonify({"ok": True})


@api_usuarios_bp.get("/api/primeiro-usuario")
def existe_usuario():
    """True quando ainda não há usuários cadastrados (para o fluxo de setup inicial)."""
    return jsonify({"vazio": usuario_repo.count() == 0})
