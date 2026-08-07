from __future__ import annotations

from flask import Flask, request, send_from_directory

from catalog_server import config
from catalog_server.blueprints import (
    api_catalog_bp,
    api_compras_bp,
    api_ia_bp,
    api_produtos_bp,
    api_quotes_bp,
    api_suppliers_bp,
    pages_bp,
    portal_bp,
)
from catalog_server.services import quote_service


def create_app() -> Flask:
    app = Flask(__name__)

    app.secret_key = config.SECRET_KEY

    # Base única: alimenta o cadastro com o que o scraper gerou (idempotente).
    from catalog_server.sync_crawler import sync_crawler

    try:
        sync_crawler()
    except Exception:
        app.logger.warning("Falha ao sincronizar produtos do scraper.", exc_info=True)

    # Índice de busca (FTS5): reconstrói no startup para cobrir produtos
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
    app.register_blueprint(api_produtos_bp)
    app.register_blueprint(api_suppliers_bp)
    app.register_blueprint(api_quotes_bp)
    app.register_blueprint(api_compras_bp)
    app.register_blueprint(api_ia_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(pages_bp)

    # Evita que o navegador use uma versão em cache de CSS/JS enquanto o
    # sistema está em desenvolvimento ativo (o index.html já tinha essa
    # proteção; os demais estáticos não tinham).
    @app.after_request
    def no_cache_estaticos(resp):
        if app.static_url_path and request.path.startswith(app.static_url_path + "/"):
            resp.headers["Cache-Control"] = "no-cache"
        return resp

    app.jinja_env.filters["brl"] = quote_service.fmt_brl
    app.jinja_env.filters["status_label"] = quote_service.status_label

    @app.get("/images/<path:name>")
    def images(name: str):
        return send_from_directory(config.IMAGES_DIR, name)

    return app
