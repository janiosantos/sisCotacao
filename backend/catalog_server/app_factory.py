from __future__ import annotations

import os
import secrets

import psycopg
from flask import Flask, abort, request, send_from_directory
from sqlalchemy.exc import OperationalError as SAOperationalError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

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
    api_contabil_bp,
    api_permissoes_bp,
    api_payments_bp,
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
    api_publico_bp,
    api_sistema_bp,
    pages_bp,
    portal_bp,
)
from catalog_server.services import quote_service
from catalog_server.services.impressao import impressao_service
from catalog_server.db import system_conn


# ─── Controle de acesso (RBAC) ────────────────────────────────────────
# Mapeia prefixo de rota /api -> recurso do catálogo de permissões.
# Rotas sem mapeamento são negadas (deny-by-default).

_RECURSO_POR_PREFIXO: list[tuple[str, str]] = [
    # Admin / sistema
    ("/api/usuarios", "usuarios"),
    ("/api/perfis", "perfis"),
    ("/api/permissoes", "perfis"),
    ("/api/flags", "configuracoes"),
    ("/api/sistema", "atualizacoes"),
    ("/api/contabil", "contabil"),
    ("/api/impressao", "impressao"),
    # Estoque / loja
    ("/api/depositos", "estoque"),
    ("/api/expedicao", "estoque"),
    ("/api/estoque", "estoque"),
    ("/api/loja", "estoque"),
    # Fiscal
    ("/api/fiscal", "fiscal"),
    ("/api/nfe", "fiscal"),
    ("/api/emitente", "fiscal"),
    ("/api/nfe-saida", "fiscal"),
    ("/api/nfe-entrada", "fiscal"),
    ("/api/ibpt", "fiscal"),
    ("/api/tecnospeed", "fiscal"),
    # Cadastros
    ("/api/produtos-cadastro", "produtos"),
    ("/api/imagens", "produtos"),
    ("/api/produtos/imagens", "produtos"),
    ("/api/familias", "produtos"),
    ("/api/marcas", "produtos"),
    ("/api/grupos", "produtos"),
    ("/api/subgrupos", "produtos"),
    ("/api/unidades-compra", "unidades"),
    ("/api/categorias-tree", "categorias"),
    ("/api/categorias", "categorias"),
    ("/api/subcategorias", "categorias"),
    ("/api/catalogo/diagnostico-variacoes", "qualidade"),
    ("/api/diagnostico", "qualidade"),
    ("/api/clientes", "clientes"),
    ("/api/fornecedores", "fornecedores"),
    ("/api/suppliers", "fornecedores"),
    ("/api/vendedores", "vendedores"),
    # Vendas
    ("/api/orcamentos", "orcamentos"),
    ("/api/politica-descontos", "orcamentos"),
    ("/api/politica-fretes", "orcamentos"),
    ("/api/cotacoes", "cotacoes"),
    ("/api/historico-precos", "historico"),
    ("/api/compras", "compras"),
    ("/api/custos", "compras"),
    ("/api/fornecedor-preco", "compras"),
    ("/api/fornecedor-preferencial", "compras"),
    ("/api/tolerancias-compra", "compras"),
    ("/api/pedidos", "compras"),
    ("/api/solicitacoes", "solicitacoes"),
    ("/api/solicitacoes-compra", "solicitacoes"),
    # Preços / financeiro
    ("/api/tabelas-preco", "precos"),
    ("/api/precos", "precos"),
    ("/api/revisoes-preco", "precos"),
    ("/api/promocoes", "precos"),
    ("/api/financeiro", "financeiro"),
    ("/api/condicoes-pagamento", "financeiro"),
    ("/api/centros-custo", "financeiro"),
    ("/api/adiantamentos", "financeiro"),
    ("/api/payment-providers", "financeiro"),
    ("/api/webhooks/payments", "financeiro"),
    ("/api/webhooks/logs", "financeiro"),
    ("/api/webhooks/rechecagem", "financeiro"),
    ("/api/webhooks/outbox", "financeiro"),
    ("/api/caixa", "caixa"),
    ("/api/bancos", "bancos"),
    ("/api/plano-contas", "plano_contas"),
    # Pós-venda / relatórios / painel
    ("/api/posvenda", "posvenda"),
    ("/api/relatorios", "dashboard"),
    ("/api/dashboard", "dashboard"),
    ("/api/produtos", "catalogo"),
    ("/api/ia", "catalogo"),
]

# Ação implícita por método HTTP (gate central).
_ACAO_POR_METODO = {
    "GET": "visualizar",
    "POST": "cadastrar",
    "PUT": "editar",
    "PATCH": "editar",
    "DELETE": "excluir",
}

# Ações específicas que não seguem o método (config/impressão).
# Chave: (método, prefixo de rota) -> ação.
_ACAO_ESPECIFICA: dict[tuple[str, str], str] = {
    ("PUT", "/api/loja/config"): "configurar",
    ("PUT", "/api/emitente"): "configurar",
    ("PUT", "/api/tecnospeed/config"): "configurar",
    ("PUT", "/api/fiscal/config/"): "configurar",
    ("POST", "/api/fiscal/config/gerar"): "configurar",
    ("POST", "/api/impressao/orcamentos/"): "imprimir",
    ("POST", "/api/impressao/teste"): "imprimir",
}

# Rotas /api públicas que exigem token válido, mas ignoram o RBAC
# (perfil próprio/sessão). Além da whitelist de auth (sem token).
_ROTAS_SEM_RBAC = {"/api/usuarios/atual"}


def _recurso_da_rota(path: str) -> str | None:
    for prefixo, recurso in _RECURSO_POR_PREFIXO:
        if path.startswith(prefixo):
            return recurso
    return None


def _acao_da_rota(path: str, method: str) -> str | None:
    """Ação da rota: específica (config/impressão) ou derivada do método."""
    especifica = _ACAO_ESPECIFICA.get((method, path))
    if especifica:
        return especifica
    # Prefixos de config que casam qualquer sub-rota (ex.: /api/fiscal/config/5)
    if method == "PUT" and path.startswith("/api/fiscal/config/"):
        return "configurar"
    return _ACAO_POR_METODO.get(method)


def _autorizar_acesso() -> None:
    """Gate central: valida permissão (recurso, ação) por rota e método.

    Controlado pela flag `CONTROLE_ACESSO` (rollback comportamental). Quando
    desligada, mantém o comportamento anterior (autenticado acessa tudo).

    Regras:
    - superuser é determinado exclusivamente pelo vínculo RBAC;
    - usuário sem relação RBAC ⇒ 403;
    - rota /api não mapeada ⇒ 403 (deny-by-default);
    - demais usuários seguem a matriz de permissões.
    """
    from catalog_server import flags, permissao

    if not flags.ativa("CONTROLE_ACESSO", default=True):
        return
    payload = getattr(request, "usuario", None)
    usuario_id = payload.get("sub") if payload else None
    if request.path in _ROTAS_SEM_RBAC:
        return
    if not usuario_id or not permissao.usuario_tem_rbac(usuario_id):
        abort(403, description="Usuário sem perfil RBAC ativo")
    recurso = _recurso_da_rota(request.path)
    if recurso is None:
        abort(403, description=f"Permissão negada: recurso não mapeado ({request.path})")
    acao = _acao_da_rota(request.path, request.method)
    if acao is None:
        abort(403, description=f"Permissão negada: método não suportado ({request.method})")
    if not permissao.tem_permissao(usuario_id, recurso, acao):
        abort(403, description=f"Permissão negada: {recurso}.{acao}")


def create_app() -> Flask:
    app = Flask(__name__)
    # Limite global de request evita uploads e payloads JSON sem teto.
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))

    app.secret_key = config.SECRET_KEY

    @app.errorhandler(HTTPException)
    def erro_http_api(e: HTTPException):
        """Mantém os erros HTTP da API em um contrato JSON estável."""
        if not request.path.startswith("/api/"):
            return e
        status = e.code or 500
        return {
            "error": e.description or e.name,
            "code": e.name.lower().replace(" ", "_"),
        }, status

    # A busca usa ILIKE + pg_trgm sobre produtos_cadastro (índices criados na
    # migração 0091) — não há mais índice derivado (produtos_fts) a reconstruir.

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
    app.register_blueprint(api_contabil_bp)
    app.register_blueprint(api_permissoes_bp)
    app.register_blueprint(api_payments_bp)
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
    app.register_blueprint(api_publico_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(pages_bp)

    # Bootstrap explícito apenas em desenvolvimento/testes. Produção usa o
    # fluxo de primeiro acesso com senha definida pelo operador.
    from catalog_server.repositories import usuario_repo

    try:
        bootstrap_password = os.getenv("CATALOG_BOOTSTRAP_ADMIN_PASSWORD") or secrets.token_urlsafe(32)
        if config.ENVIRONMENT != "production" and usuario_repo.count() == 0:
            from werkzeug.security import generate_password_hash

            admin_id = usuario_repo.create(
                "Administrador", "admin", generate_password_hash(bootstrap_password)
            )
            # Vincula ao perfil RBAC Administrador (superuser) — Contract 0077.
            from catalog_server import permissao as _permissao

            with system_conn() as _conn:
                row = _conn.execute(
                    "SELECT id FROM perfis WHERE nome='Administrador'"
                ).fetchone()
            if row:
                _permissao.definir_perfis(admin_id, [row["id"]])
            app.logger.warning(
                "Admin inicial criado. Defina CATALOG_BOOTSTRAP_ADMIN_PASSWORD "
                "antes de iniciar o ambiente para controlar a senha."
            )
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

    # CORS para a API pública (site institucional consome de outro domínio).
    @app.after_request
    def cors_publico(resp):
        if request.path.startswith("/api/publico/"):
            permitidas = {
                origem.strip()
                for origem in os.getenv(
                    "PUBLIC_CORS_ORIGINS",
                    "https://casalm.com.br,https://www.casalm.com.br,http://localhost:4321,http://localhost:8080,http://127.0.0.1:4321,http://127.0.0.1:8080",
                ).split(",")
                if origem.strip()
            }
            origem = request.headers.get("Origin", "").strip()
            if origem in permitidas:
                resp.headers["Access-Control-Allow-Origin"] = origem
                resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return resp

    # Rotas /api abertas (sem token): health, login e o fluxo de primeiro
    # acesso (criação do admin inicial e checagem de "vazio").
    _WHITELIST = {
        "/api/health": {"GET"},
        "/api/pronto": {"GET"},
        "/api/openapi.json": {"GET"},
        "/api/login": {"POST"},
        "/api/logout": {"POST"},
        "/api/primeiro-usuario": {"GET"},
        "/api/webhooks/tecnospeed": {"POST"},  # callback público da SEFAZ/Tecnospeed
        "/api/webhooks/payments": {"POST"},  # webhooks de pagamento (Asaas/Mercado Pago)
    }

    @app.before_request
    def exigir_token():
        if not request.path.startswith("/api/"):
            return
        # Portal do fornecedor: usa token próprio na URL, fora da auth da API.
        if request.path.startswith("/api/fornecedor/"):
            return
        # API pública (site institucional): somente leitura, sem token.
        if request.path.startswith("/api/publico/") and request.method in ("GET", "OPTIONS"):
            return
        # Criação anônima só existe enquanto o banco estiver sem usuários.
        # Depois do bootstrap, a rota passa pelo Bearer/RBAC normal.
        if request.path == "/api/usuarios" and request.method == "POST":
            with system_conn() as conn:
                vazio = not conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone()
            if vazio:
                return
        metodos = _WHITELIST.get(request.path)
        if metodos and request.method in metodos:
            return
        # Webhooks de pagamento com provedor na URL: /api/webhooks/payments/<provider>
        if request.path.startswith("/api/webhooks/payments/") and request.method == "POST":
            return
        # Perfil próprio: sempre acessível (dados de sessão, não gestão de usuários).
        if request.path == "/api/usuarios/atual":
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                abort(401, description="Token de API ausente")
            payload = auth_token.validar_token(auth[7:])
            if not payload:
                abort(401, description="Token de API inválido ou expirado")
            with system_conn() as conn:
                ativo = conn.execute(
                    "SELECT ativo FROM usuarios WHERE id=?", (payload.get("sub"),)
                ).fetchone()
            if not ativo or not ativo["ativo"]:
                abort(401, description="Usuário inativo ou inexistente")
            request.usuario = payload
            return
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            abort(401, description="Token de API ausente")
        payload = auth_token.validar_token(auth[7:])
        if not payload:
            abort(401, description="Token de API inválido ou expirado")
        with system_conn() as conn:
            ativo = conn.execute(
                "SELECT ativo FROM usuarios WHERE id=?", (payload.get("sub"),)
            ).fetchone()
        if not ativo or not ativo["ativo"]:
            abort(401, description="Usuário inativo ou inexistente")
        request.usuario = payload
        _autorizar_acesso()

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

    @app.errorhandler(RequestEntityTooLarge)
    def payload_grande_demais(e):
        return {"error": "Payload ou arquivo excede o limite permitido", "code": "payload_too_large"}, 413

    # Retaguarda de impressão: passa a drenar a fila de cupons assim que o
    # sistema estiver de pé.
    impressao_service.start_worker()

    return app
