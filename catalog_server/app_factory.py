from __future__ import annotations

import psycopg
from flask import Flask, abort, request, send_from_directory
from sqlalchemy.exc import OperationalError as SAOperationalError

from catalog_server import auth_token, config
from catalog_server.blueprints import (
    api_bancos_bp,
    api_compras_avancado_bp,
    api_posvenda_bp,
    api_catalog_bp,
    api_dashboard_bp,
    api_diagnostico_bp,
    api_loja_bp,
    api_clientes_bp,
    api_compras_bp,
    api_estoque_bp,
    api_financeiro_bp,
    api_fiscal_avancado_bp,
    api_fiscal_bp,
    api_fiscal_docs_bp,
    api_fiscal_regras_bp,
    api_relatorios_bp,
    api_precos_bp,
    api_ia_bp,
    api_impressao_bp,
    api_orcamentos_bp,
    api_plano_contas_bp,
    api_produtos_bp,
    api_quotes_bp,
    api_suppliers_bp,
    api_usuarios_bp,
    api_vendedores_bp,
    api_sistema_bp,
    pages_bp,
    portal_bp,
)
from catalog_server.services import quote_service
from catalog_server.services.impressao import impressao_service


def create_app() -> Flask:
    app = Flask(__name__)

    app.secret_key = config.SECRET_KEY

    # Índice de busca (tsvector): reconstrói no startup para cobrir produtos
    # cadastrados antes do índice existir.
    from catalog_server import fts
    from catalog_server.db import system_conn

    try:
        with system_conn() as conn:
            fts.ensure_fts(conn)
            if fts.is_empty(conn):
                fts.rebuild(conn)
    except Exception:
        app.logger.warning("Falha ao indexar a busca de produtos (FTS).", exc_info=True)

    app.register_blueprint(api_catalog_bp)
    app.register_blueprint(api_dashboard_bp)
    app.register_blueprint(api_diagnostico_bp)
    app.register_blueprint(api_loja_bp)
    app.register_blueprint(api_produtos_bp)
    app.register_blueprint(api_suppliers_bp)
    app.register_blueprint(api_quotes_bp)
    app.register_blueprint(api_orcamentos_bp)
    app.register_blueprint(api_impressao_bp)
    app.register_blueprint(api_compras_bp)
    app.register_blueprint(api_ia_bp)
    app.register_blueprint(api_usuarios_bp)
    app.register_blueprint(api_vendedores_bp)
    app.register_blueprint(api_clientes_bp)
    app.register_blueprint(api_plano_contas_bp)
    app.register_blueprint(api_bancos_bp)
    app.register_blueprint(api_compras_avancado_bp)
    app.register_blueprint(api_posvenda_bp)
    app.register_blueprint(api_estoque_bp)
    app.register_blueprint(api_financeiro_bp)
    app.register_blueprint(api_fiscal_avancado_bp)
    app.register_blueprint(api_fiscal_bp)
    app.register_blueprint(api_fiscal_docs_bp)
    app.register_blueprint(api_fiscal_regras_bp)
    app.register_blueprint(api_precos_bp)
    app.register_blueprint(api_relatorios_bp)
    app.register_blueprint(api_sistema_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(pages_bp)

    # Primeiro acesso: garante um usuário admin inicial quando ainda não existe
    # nenhum (senha padrão "admin123" — troque logo após o primeiro login).
    from catalog_server.repositories import usuario_repo

    try:
        if usuario_repo.count() == 0:
            from werkzeug.security import generate_password_hash

            usuario_repo.create("Administrador", "admin", generate_password_hash("admin123"), "admin")
    except Exception:
        app.logger.warning("Falha ao criar usuário admin inicial.", exc_info=True)

    # Cliente padrão (id 1 — CONSUMIDOR) usado quando o vendedor não informa cliente.
    from catalog_server.repositories.clientes import cliente_repo

    try:
        cliente_repo.garantir_padrao()
    except Exception:
        app.logger.warning("Falha ao garantir cliente padrão.", exc_info=True)

    # Evita que o navegador use uma versão em cache de CSS/JS enquanto o
    # sistema está em desenvolvimento ativo (o index.html já tinha essa
    # proteção; os demais estáticos não tinham).
    @app.after_request
    def no_cache_estaticos(resp):
        if app.static_url_path and request.path.startswith(app.static_url_path + "/"):
            resp.headers["Cache-Control"] = "no-cache"
        return resp

    # Rotas /api abertas (sem token): health, login e o fluxo de primeiro
    # acesso (criação do admin inicial e checagem de "vazio").
    _WHITELIST = {
        "/api/health": {"GET"},
        "/api/pronto": {"GET"},
        "/api/login": {"POST"},
        "/api/logout": {"POST"},
        "/api/primeiro-usuario": {"GET"},
        "/api/usuarios": {"POST"},  # criação do primeiro administrador
    }

    @app.before_request
    def exigir_token():
        if not request.path.startswith("/api/"):
            return
        # Portal do fornecedor: usa token próprio na URL, fora da auth da API.
        if request.path.startswith("/api/fornecedor/"):
            return
        metodos = _WHITELIST.get(request.path)
        if metodos and request.method in metodos:
            return
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            abort(401, description="Token de API ausente")
        payload = auth_token.validar_token(auth[7:])
        if not payload:
            abort(401, description="Token de API inválido ou expirado")
        request.usuario = payload

    app.jinja_env.filters["brl"] = quote_service.fmt_brl
    app.jinja_env.filters["qty"] = quote_service.fmt_qty
    app.jinja_env.filters["status_label"] = quote_service.status_label

    @app.get("/images/<path:name>")
    def images(name: str):
        return send_from_directory(config.IMAGES_DIR, name)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}, 200

    # Readiness: sinaliza se o sistema está utilizável (banco acessível).
    # Diferente do /api/health (liveness do container), aqui o banco é checado
    # de verdade — o frontend usa este endpoint para o modo manutenção.
    @app.get("/api/pronto")
    def pronto():
        try:
            with system_conn() as conn:
                conn.execute("SELECT 1").fetchone()
            return {"pronto": True}, 200
        except Exception:
            return (
                {"pronto": False, "error": "Banco de dados indisponível", "code": "db_indisponivel"},
                503,
            )

    # Banco fora do ar (deploy, manutenção, rede): resposta limpa em vez de
    # 500 genérico — o frontend reconhece e entra em modo manutenção.
    @app.errorhandler(SAOperationalError)
    @app.errorhandler(psycopg.OperationalError)
    def db_indisponivel(e):
        return (
            {"error": "Banco de dados indisponível", "code": "db_indisponivel"},
            503,
        )

    # Retaguarda de impressão: passa a drenar a fila de cupons assim que o
    # sistema estiver de pé.
    impressao_service.start_worker()

    return app
