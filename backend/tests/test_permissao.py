"""Controle de acesso por perfil (RBAC) — migração 0075."""
from __future__ import annotations

import json
import base64
import time

import pytest

from catalog_server import permissao
from catalog_server.db import system_conn
from catalog_server.repositories import usuario_repo


def _criar_usuario(login: str = "teste") -> int:
    from werkzeug.security import generate_password_hash

    with system_conn() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome, login, senha_hash) VALUES (%s,%s,%s)",
            ("Teste", login, generate_password_hash("x123")),
        )
        return int(cur.lastrowid)


def _perfil_id(nome: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM perfis WHERE nome=%s", (nome,)
        ).fetchone()["id"])


def _recurso_id(codigo: str) -> int:
    with system_conn() as conn:
        return int(conn.execute(
            "SELECT id FROM recursos WHERE codigo=%s", (codigo,)
        ).fetchone()["id"])


def _vincular(usuario_id: int, nome_perfil: str) -> None:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_perfis (usuario_id, perfil_id) VALUES (%s,%s)"
            " ON CONFLICT DO NOTHING",
            (usuario_id, _perfil_id(nome_perfil)),
        )
        conn.commit()
    permissao.invalidar(usuario_id)


def test_perfis_seedados_e_administrador_superuser(system_db):
    with system_conn() as conn:
        nomes = sorted(r["nome"] for r in conn.execute("SELECT nome FROM perfis").fetchall())
    assert nomes == ["Administrador", "Estoquista", "Operador", "Vendedor"]

    uid = _criar_usuario("admteste")
    _vincular(uid, "Administrador")
    assert permissao.tem_permissao(uid, "usuarios", "excluir") is True
    assert permissao.tem_permissao(uid, "qualquer_recurso", "qualquer_acao") is True


def test_vendedor_preset_limita_acesso(system_db):
    uid = _criar_usuario("vendteste")
    _vincular(uid, "Vendedor")
    # Permissões do preset
    assert permissao.tem_permissao(uid, "pre-venda", "cadastrar") is True
    assert permissao.tem_permissao(uid, "orcamentos", "imprimir") is True
    assert permissao.tem_permissao(uid, "clientes", "editar") is True
    # Fora do preset
    assert permissao.tem_permissao(uid, "produtos", "excluir") is False
    assert permissao.tem_permissao(uid, "usuarios", "visualizar") is False
    assert permissao.tem_permissao(uid, "estoque", "visualizar") is False


def test_multiplos_perfis_uniao(system_db):
    uid = _criar_usuario("multi")
    _vincular(uid, "Vendedor")
    _vincular(uid, "Estoquista")
    # União: estoque vem do Estoquista, pre-venda do Vendedor
    assert permissao.tem_permissao(uid, "estoque", "cadastrar") is True
    assert permissao.tem_permissao(uid, "pre-venda", "cadastrar") is True
    # Não concedido por nenhum dos dois
    assert permissao.tem_permissao(uid, "usuarios", "visualizar") is False


def test_override_concede_extra(system_db):
    uid = _criar_usuario("over")
    _vincular(uid, "Vendedor")
    assert permissao.tem_permissao(uid, "produtos", "visualizar") is False

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_override (usuario_id, recurso_id, acoes_extra)"
            " VALUES (%s,%s,%s)",
            (uid, _recurso_id("produtos"), json.dumps(["visualizar", "cadastrar"])),
        )
        conn.commit()
    permissao.invalidar(uid)
    assert permissao.tem_permissao(uid, "produtos", "visualizar") is True
    assert permissao.tem_permissao(uid, "produtos", "cadastrar") is True
    assert permissao.tem_permissao(uid, "produtos", "excluir") is False


def test_negacao_remove_acao(system_db):
    """Negação por usuário remove ação mesmo quando o perfil concede."""
    uid = _criar_usuario("negar")
    _vincular(uid, "Vendedor")
    # Vendedor concede pre-venda.cadastrar
    assert permissao.tem_permissao(uid, "pre-venda", "cadastrar") is True

    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_override (usuario_id, recurso_id, acoes_extra, acoes_negadas)"
            " VALUES (%s,%s,%s,%s)",
            (uid, _recurso_id("pre-venda"), json.dumps([]), json.dumps(["cadastrar"])),
        )
        conn.commit()
    permissao.invalidar(uid)
    assert permissao.tem_permissao(uid, "pre-venda", "cadastrar") is False
    # Visualizar continua (perfil concede e não foi negado)
    assert permissao.tem_permissao(uid, "pre-venda", "visualizar") is True


def test_negacao_nao_afeta_superuser(system_db):
    """Administrador ignora negação por usuário."""
    uid = _criar_usuario("negaradm")
    _vincular(uid, "Administrador")
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO usuario_override (usuario_id, recurso_id, acoes_extra, acoes_negadas)"
            " VALUES (%s,%s,%s,%s)",
            (uid, _recurso_id("usuarios"), json.dumps([]), json.dumps(["visualizar"])),
        )
        conn.commit()
    permissao.invalidar(uid)
    assert permissao.tem_permissao(uid, "usuarios", "visualizar") is True


def test_crud_perfil(system_db):
    """CRUD de perfis novos (dívida 2)."""
    # Criar
    pid = permissao.criar_perfil("Gerente", "Gestão de vendas")
    with system_conn() as conn:
        nome = conn.execute("SELECT nome FROM perfis WHERE id=%s", (pid,)).fetchone()["nome"]
    assert nome == "Gerente"

    # Renomear
    assert permissao.atualizar_perfil(pid, "Gerente Sênior", "Vendas") is True
    with system_conn() as conn:
        nome = conn.execute("SELECT nome FROM perfis WHERE id=%s", (pid,)).fetchone()["nome"]
    assert nome == "Gerente Sênior"

    # Reservado: Administrador não pode ser criado/renomeado/excluído
    import pytest

    with pytest.raises(ValueError):
        permissao.criar_perfil("Administrador")
    with pytest.raises(ValueError):
        permissao.atualizar_perfil(_perfil_id("Administrador"), "Outro", "")

    # Desativar e excluir sem vínculo
    assert permissao.set_perfil_ativo(pid, False) is True
    assert permissao.excluir_perfil(pid) is True
    with system_conn() as conn:
        existe = conn.execute("SELECT 1 FROM perfis WHERE id=%s", (pid,)).fetchone()
    assert existe is None


def test_excluir_perfil_em_uso_bloqueia(system_db):
    import pytest

    pid = permissao.criar_perfil("EmUso", "")
    uid = _criar_usuario("usou")
    _vincular(uid, "EmUso")
    with pytest.raises(ValueError):
        permissao.excluir_perfil(pid)


def test_backfill_usuarios_existentes(system_db):
    # O backfill roda na migração (usuário com perfil legado vira Administrador).
    # Aqui valida o fluxo: criar usuário e vincular ao perfil Administrador.
    uid = _criar_usuario("backfill")
    _vincular(uid, "Administrador")
    assert permissao.tem_permissao(uid, "usuarios", "excluir") is True


def test_acoes_reconhecidas():
    assert "visualizar" in permissao.ACOES
    assert "configurar" in permissao.ACOES


def test_gate_central_rota_para_recurso(system_db):
    # Validar o mapeamento rota -> recurso (não muda o estado do banco)
    from catalog_server.app_factory import _recurso_da_rota

    assert _recurso_da_rota("/api/produtos-cadastro/1") == "produtos"
    assert _recurso_da_rota("/api/estoque/saldo") == "estoque"
    assert _recurso_da_rota("/api/usuarios") == "usuarios"
    assert _recurso_da_rota("/api/orcamentos/5/autorizar-desconto") == "orcamentos"
    assert _recurso_da_rota("/api/catalogo/diagnostico-variacoes") == "qualidade"
    assert _recurso_da_rota("/api/historico-precos") == "historico"
    assert _recurso_da_rota("/api/ibpt/sugestoes") == "fiscal"
    assert _recurso_da_rota("/api/condicoes-pagamento") == "financeiro"
    assert _recurso_da_rota("/api/politica-descontos") == "orcamentos"
    assert _recurso_da_rota("/api/fornecedor-preco") == "compras"
    assert _recurso_da_rota("/api/rota-desconhecida") is None


def test_mapeamento_100pct_rotas_api(system_db):
    """Toda rota /api registrada deve mapear para um recurso (dívida 1).

    Exceções: allowlist de auth (sem token) e portal do fornecedor (token
    próprio na URL) — verificadas aqui para garantir cobertura total.
    """
    from catalog_server.app_factory import _recurso_da_rota, create_app

    app = create_app()
    whitelist = {
        "/api/health",
        "/api/pronto",
        "/api/openapi.json",
        "/api/login",
        "/api/logout",
        "/api/primeiro-usuario",
        "/api/webhooks/tecnospeed",
    }
    nao_mapeadas: list[str] = []
    for rule in app.url_map.iter_rules():
        path = rule.rule
        if not path.startswith("/api/"):
            continue
        # POST /api/usuarios (criação do primeiro admin) e portal do fornecedor
        if path == "/api/usuarios":
            continue
        if path.startswith("/api/fornecedor/"):
            continue
        # API pública (site institucional): leitura sem token, fora do RBAC.
        if path.startswith("/api/publico/"):
            continue
        if path in whitelist:
            continue
        if _recurso_da_rota(path) is None:
            nao_mapeadas.append(path)
    assert nao_mapeadas == [], f"Rotas /api sem mapeamento: {nao_mapeadas}"


def test_endpoint_requer_permissao_com_app(system_db):
    """O gate central bloqueia POST sem permissão de cadastrar."""
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    # Usuário vendedor: NÃO tem permissão em 'produtos'
    uid = _criar_usuario("gatev")
    _vincular(uid, "Vendedor")
    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": uid, "login": "gatev"})
    h = {"Authorization": f"Bearer {tok}"}

    # POST /api/produtos-cadastro -> cadastrar em produtos (negado p/ vendedor)
    r = c.post("/api/produtos-cadastro", json={"nome": "x"}, headers=h)
    assert r.status_code == 403
    # GET /api/produtos -> catalogo (vendedor visualiza)
    r2 = c.get("/api/produtos?q=x", headers=h)
    assert r2.status_code == 200


def test_deny_by_default_rota_nao_mapeada(system_db):
    """Rota /api não mapeada retorna 403 para usuário com RBAC (deny-by-default)."""
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    uid = _criar_usuario("denydef")
    _vincular(uid, "Vendedor")
    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": uid, "login": "denydef"})
    h = {"Authorization": f"Bearer {tok}"}
    r = c.get("/api/rota-inexistente", headers=h)
    assert r.status_code == 403


def test_admin_passacheck_no_gate(system_db):
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    uid = _criar_usuario("gateadm")
    _vincular(uid, "Administrador")
    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": uid, "login": "gateadm"})
    h = {"Authorization": f"Bearer {tok}"}
    r = c.delete("/api/produtos-cadastro/9999", headers=h)
    # 404 (produto não existe) e não 403 — admin passou no gate
    assert r.status_code == 404


def test_admin_pode_cadastrar_cliente_pelo_pdv(system_db):
    """O superusuário Administrador passa o gate do cadastro rápido do PDV."""
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    uid = _criar_usuario("gateadmcliente")
    _vincular(uid, "Administrador")
    app = create_app()
    c = app.test_client()
    tok = auth_token.criar_token({"id": uid, "login": "gateadmcliente"})

    r = c.post(
        "/api/clientes",
        json={"nome": "Cliente criado pelo teste", "doc": "12345678909"},
        headers={"Authorization": f"Bearer {tok}"},
    )

    assert r.status_code == 201, r.get_json()
    assert r.get_json()["id"] > 1


def test_webhook_publico_sem_token(system_db):
    """Webhook Tecnospeed é público (sem token) — whitelist de auth."""
    from catalog_server.app_factory import create_app

    c = create_app().test_client()
    r = c.post("/api/webhooks/tecnospeed", json={})
    # Sem token deve passar pela auth (whitelist); resposta depende do handler.
    assert r.status_code != 401


def test_acoes_sensiveis_mapeiam_para_acao_correta():
    from catalog_server.app_factory import _acao_da_rota

    assert _acao_da_rota("/api/impressao/orcamentos/10", "POST") == "imprimir"
    assert _acao_da_rota("/api/orcamentos/10/nfce", "POST") == "emitir"
    assert _acao_da_rota("/api/orcamentos/10/nfe", "POST") == "emitir"
    assert _acao_da_rota("/api/orcamentos/10/focus/65", "POST") == "emitir"
    assert _acao_da_rota("/api/orcamentos/10/rejeitar-desconto", "POST") == "cadastrar"


def test_perfil_admin_nao_pode_ser_removido_se_for_o_ultimo(system_db):
    uid = _criar_usuario("ultimoadm")
    _vincular(uid, "Administrador")

    with pytest.raises(ValueError, match="último administrador"):
        permissao.definir_perfis(uid, [_perfil_id("Vendedor")])


def test_usuario_sem_perfil_pode_ser_resultado_de_revogacao(system_db):
    admin = _criar_usuario("rbacadminrev")
    _vincular(admin, "Administrador")
    alvo = _criar_usuario("rbacalvo")
    _vincular(alvo, "Vendedor")
    permissao.definir_overrides(alvo, conceder={"produtos": ["visualizar"]})

    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    token = auth_token.criar_token({"id": admin, "login": "rbacadminrev"})
    response = create_app().test_client().put(
        f"/api/usuarios/{alvo}",
        json={"nome": "Alvo", "perfil_ids": [], "conceder": {}, "negar": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.get_json()
    assert permissao.usuario_tem_rbac(alvo) is False
    assert permissao.listar_auditoria(usuario_id=alvo)


def test_usuario_nao_admin_nao_administra_rbac(system_db):
    uid = _criar_usuario("rbacvendedor")
    _vincular(uid, "Vendedor")
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    token = auth_token.criar_token({"id": uid, "login": "rbacvendedor"})
    response = create_app().test_client().post(
        "/api/usuarios",
        json={"nome": "Escalada", "login": "escalada", "senha": "x123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_logout_revoga_token_emitido(system_db):
    uid = _criar_usuario("logoutrev")
    _vincular(uid, "Administrador")
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    token = auth_token.criar_token({"id": uid, "login": "logoutrev"})
    client = create_app().test_client()
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/usuarios/atual", headers=headers).status_code == 200
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/usuarios/atual", headers=headers).status_code == 401


def test_usuario_atual_expoe_expiracao_e_versao(system_db, monkeypatch):
    uid = _criar_usuario("statussessao")
    _vincular(uid, "Administrador")
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    monkeypatch.setenv("APP_VERSION", "v-teste")
    token = auth_token.criar_token({"id": uid, "login": "statussessao"}, ttl=300)
    response = create_app().test_client().get(
        "/api/usuarios/atual",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["app_version"] == "v-teste"
    assert data["sessao_expira_em"] > 0


def test_token_legado_sem_versao_e_rejeitado(system_db):
    uid = _criar_usuario("tokenlegado")
    _vincular(uid, "Administrador")
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    payload = {"sub": uid, "login": "tokenlegado", "exp": int(time.time()) + 300}
    data = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    token = f"{data}.{auth_token._sign(data)}"
    response = create_app().test_client().get(
        "/api/usuarios/atual",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_admin_nao_pode_remover_a_propria_ultima_conta_ativa(system_db):
    uid = _criar_usuario("autobloqueio")
    _vincular(uid, "Administrador")

    with pytest.raises(ValueError, match="própria conta"):
        permissao.alterar_ativo(uid, uid, False)


def test_usuario_vendedor_nao_alcanca_emissao_fiscal(system_db):
    uid = _criar_usuario("semfiscal")
    _vincular(uid, "Vendedor")
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    token = auth_token.criar_token({"id": uid, "login": "semfiscal"})
    response = create_app().test_client().post(
        "/api/orcamentos/999999/nfce",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_alteracao_de_perfil_registra_auditoria_com_ator(system_db):
    admin = _criar_usuario("auditadmin")
    _vincular(admin, "Administrador")
    alvo = _criar_usuario("auditalvo")
    _vincular(alvo, "Vendedor")

    permissao.definir_perfis(
        alvo, [_perfil_id("Operador")], actor_id=admin, ip="127.0.0.1"
    )
    eventos = permissao.listar_auditoria(usuario_id=alvo)
    assert eventos
    assert eventos[0]["actor_usuario_id"] == admin
    assert eventos[0]["operacao"] == "definir_perfis"


def test_payload_rbac_invalido_nao_cria_usuario_parcialmente(system_db):
    admin = _criar_usuario("adminpayload")
    _vincular(admin, "Administrador")
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    token = auth_token.criar_token({"id": admin, "login": "adminpayload"})
    response = create_app().test_client().post(
        "/api/usuarios",
        json={
            "nome": "Usuário inválido",
            "login": "usuariorbacinvalido",
            "senha": "x123",
            "perfil_ids": [999999],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert usuario_repo.get_by_login("usuariorbacinvalido") is None


def test_matriz_rbac_invalida_nao_cria_perfil_parcialmente(system_db):
    admin = _criar_usuario("adminmatriz")
    _vincular(admin, "Administrador")
    from catalog_server import auth_token
    from catalog_server.app_factory import create_app

    token = auth_token.criar_token({"id": admin, "login": "adminmatriz"})
    response = create_app().test_client().post(
        "/api/perfis",
        json={"nome": "Perfil inválido", "permissoes": {"nao_existe": ["visualizar"]}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    with system_conn() as conn:
        assert conn.execute(
            "SELECT 1 FROM perfis WHERE nome=%s", ("Perfil inválido",)
        ).fetchone() is None
