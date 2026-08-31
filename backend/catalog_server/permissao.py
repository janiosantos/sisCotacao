"""Controle de acesso por perfil (RBAC) — migração 0075.

Usuário pode ter múltiplos perfis (união das permissões) e overrides por
recurso: `acoes_extra` CONCEDEM ações extras e `acoes_negadas` NEGAM ações
(pontuais). A efetiva é `(perfis ∪ conceder) − negar`. O perfil
"Administrador" é superuser: ignora todas as checagens, inclusive negações.

Uso em blueprints:

    from catalog_server import permissao

    # decorator para endpoints específicos
    @permissao.exige_permissao("orcamentos", "aprovar")
    def autorizar_desconto(...): ...

    # checagem explícita (se necessário)
    if not permissao.tem_permissao(usuario_id, "produtos", "excluir"):
        abort(403, description="Permissão negada")
"""
from __future__ import annotations

import functools
import json
import threading
import time

from flask import abort

from catalog_server.db import system_conn

_ACOES = ("visualizar", "cadastrar", "editar", "excluir", "imprimir", "aprovar", "configurar", "emitir")

# Alias público (usado por blueprints e testes).
ACOES = _ACOES

_PERFIL_ADMIN = "Administrador"

_TTL = 30.0  # segundos de cache em processo
_lock = threading.Lock()
_cache: dict[int, tuple[float, dict[str, set[str]]]] = {}


def _carregar(usuario_id: int) -> dict[str, set[str]]:
    """Permissões efetivas do usuário: (perfis ∪ conceder) − negar.

    O perfil Administrador devolve um sentinela que faz `tem_permissao`
    responder sempre True (ignora inclusive negações por usuário).
    """
    with _lock:
        agora = time.monotonic()
        hit = _cache.get(usuario_id)
        if hit and (agora - hit[0]) < _TTL:
            return hit[1]

    acoes: dict[str, set[str]] = {}
    with system_conn() as conn:
        # Perfil Administrador => superuser.
        row = conn.execute(
            "SELECT 1 FROM usuario_perfis up JOIN perfis p ON p.id=up.perfil_id"
            " JOIN usuarios u ON u.id=up.usuario_id"
            " WHERE up.usuario_id=? AND u.ativo=1 AND p.ativo=1 AND p.nome=?",
            (usuario_id, _PERFIL_ADMIN),
        ).fetchone()
        if row:
            sentinela = {"__superuser__"}
            with _lock:
                _cache[usuario_id] = (time.monotonic(), sentinela)
            return sentinela

        rows = conn.execute(
            """
            SELECT r.codigo AS recurso, pr.acoes
            FROM usuario_perfis up
            JOIN perfis p ON p.id = up.perfil_id
            JOIN perfil_recurso pr ON pr.perfil_id = p.id
            JOIN recursos r ON r.id = pr.recurso_id
            WHERE up.usuario_id = ? AND p.ativo = 1 AND r.ativo = 1
            """,
            (usuario_id,),
        ).fetchall()
        for r in rows:
            _merge_acoes(acoes, r["recurso"], r["acoes"])

        rows_ov = conn.execute(
            """
            SELECT r.codigo AS recurso, uo.acoes_extra
            FROM usuario_override uo
            JOIN recursos r ON r.id = uo.recurso_id
            WHERE uo.usuario_id = ? AND r.ativo = 1
            """,
            (usuario_id,),
        ).fetchall()
        for r in rows_ov:
            _merge_acoes(acoes, r["recurso"], r["acoes_extra"])

        rows_neg = conn.execute(
            """
            SELECT r.codigo AS recurso, uo.acoes_negadas
            FROM usuario_override uo
            JOIN recursos r ON r.id = uo.recurso_id
            WHERE uo.usuario_id = ? AND r.ativo = 1
            """,
            (usuario_id,),
        ).fetchall()
        for r in rows_neg:
            _remove_acoes(acoes, r["recurso"], r["acoes_negadas"])

    with _lock:
        _cache[usuario_id] = (time.monotonic(), acoes)
    return acoes


def _merge_acoes(acoes: dict[str, set[str]], recurso, valor) -> None:
    """Mescla o JSON de ações (lista de strings) no mapa do usuário."""
    lista = _parse_lista(valor)
    alvo = acoes.setdefault(str(recurso), set())
    for a in lista:
        if a in _ACOES:
            alvo.add(a)


def _remove_acoes(acoes: dict[str, set[str]], recurso, valor) -> None:
    """Remove as ações negadas do mapa (negação por usuário)."""
    lista = _parse_lista(valor)
    alvo = acoes.get(str(recurso))
    if alvo is None:
        return
    for a in lista:
        alvo.discard(a)
    if not alvo:
        acoes.pop(str(recurso), None)


def _parse_lista(valor) -> list[str]:
    if isinstance(valor, list):
        return [a for a in valor if a in _ACOES]
    try:
        lista = json.loads(valor) if isinstance(valor, str) else []
    except (TypeError, ValueError):
        lista = []
    return [a for a in lista if a in _ACOES]


def tem_permissao(usuario_id: int | None, recurso: str, acao: str) -> bool:
    """True quando o usuário pode `acao` em `recurso` (admin sempre True)."""
    if not usuario_id:
        return False
    acoes = _carregar(usuario_id)
    if "__superuser__" in acoes:
        return True
    return acao in acoes.get(recurso, set())


def usuario_e_superuser(usuario_id: int | None) -> bool:
    """Retorna se o usuário ativo possui o perfil Administrador ativo."""
    if not usuario_id:
        return False
    with system_conn() as conn:
        return _superuser_na_conn(conn, usuario_id)


def _superuser_na_conn(conn, usuario_id: int | None) -> bool:
    if not usuario_id:
        return False
    return bool(conn.execute(
            "SELECT 1 FROM usuario_perfis up "
            "JOIN perfis p ON p.id=up.perfil_id "
            "JOIN usuarios u ON u.id=up.usuario_id "
            "WHERE up.usuario_id=? AND u.ativo=1 AND p.ativo=1 AND p.nome=?",
            (usuario_id, _PERFIL_ADMIN),
        ).fetchone())


def usuario_tem_rbac(usuario_id: int | None) -> bool:
    """True quando o usuário possui alguma relação RBAC (perfil ou override).

    Usado pelo gate central para preservar o comportamento de transição:
    usuários ainda não vinculados a nenhum perfil (ex.: criados antes da
    migração) seguem liberados até serem associados.
    """
    if not usuario_id:
        return False
    with system_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM usuario_perfis WHERE usuario_id=? LIMIT 1",
            (usuario_id,),
        ).fetchone()
        if row:
            return True
        row2 = conn.execute(
            "SELECT 1 FROM usuario_override WHERE usuario_id=? LIMIT 1",
            (usuario_id,),
        ).fetchone()
        return bool(row2)


def invalidar(usuario_id: int | None = None) -> None:
    """Invalida o cache (todos ou de um usuário) após gravações."""
    global _cache
    with _lock:
        if usuario_id is None:
            _cache = {}
        else:
            _cache.pop(usuario_id, None)


def validar_perfil_ids(
    perfil_ids: list[int], *, actor_id: int | None = None
) -> list[int]:
    """Valida um conjunto de perfis antes de alterar dados do usuário."""
    if not isinstance(perfil_ids, list):
        raise ValueError("perfil_ids deve ser uma lista")
    try:
        ids = list(dict.fromkeys(int(pid) for pid in perfil_ids))
    except (TypeError, ValueError):
        raise ValueError("perfil_ids contém um valor inválido") from None
    with system_conn() as conn:
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT id, nome, ativo FROM perfis WHERE id IN ({placeholders})",
            tuple(ids),
        ).fetchall() if ids else []
        if len({int(row["id"]) for row in rows}) != len(ids) or any(
            not row["ativo"] for row in rows
        ):
            raise ValueError("Um ou mais perfis não existem ou estão inativos")
        if any(row["nome"] == _PERFIL_ADMIN for row in rows):
            if actor_id and not _superuser_na_conn(conn, actor_id):
                raise ValueError("Somente um Administrador pode atribuir o perfil Administrador")
    return ids


def validar_overrides_payload(
    conceder: dict[str, list[str]] | None = None,
    negar: dict[str, list[str]] | None = None,
    *,
    overrides: dict[str, list[str]] | None = None,
) -> None:
    """Valida overrides antes de executar uma alteração em outra tabela."""
    conceder_map = conceder if conceder is not None else (overrides or {})
    negar_map = negar or {}
    if not isinstance(conceder_map, dict) or not isinstance(negar_map, dict):
        raise ValueError("Overrides devem ser objetos recurso -> ações")
    with system_conn() as conn:
        recursos = {r["codigo"] for r in conn.execute("SELECT codigo FROM recursos")}
    for codigo in set(conceder_map) | set(negar_map):
        if str(codigo) not in recursos:
            raise ValueError(f"Recurso inválido: {codigo}")
        concedidas = conceder_map.get(codigo, [])
        negadas = negar_map.get(codigo, [])
        if not isinstance(concedidas, list) or not isinstance(negadas, list):
            raise ValueError(f"Ações inválidas para o recurso: {codigo}")
        desconhecidas = [a for a in [*concedidas, *negadas] if a not in _ACOES]
        if desconhecidas:
            raise ValueError(f"Ação inválida: {desconhecidas[0]}")


# ─── Gravação da relação RBAC (usada por api_usuarios e api_permissoes) ───

def _snapshot_perfis(conn, usuario_id: int) -> list[dict]:
    return [dict(row) for row in conn.execute(
        "SELECT p.id, p.nome, p.ativo FROM usuario_perfis up "
        "JOIN perfis p ON p.id=up.perfil_id WHERE up.usuario_id=? ORDER BY p.id",
        (usuario_id,),
    ).fetchall()]


def _registrar_auditoria(
    conn,
    *,
    actor_id: int | None,
    target_usuario_id: int | None,
    target_perfil_id: int | None = None,
    operacao: str,
    recurso: str | None = None,
    antes=None,
    depois=None,
    motivo: str = "",
    ip: str | None = None,
) -> None:
    if not actor_id:
        return
    conn.execute(
        "INSERT INTO rbac_audit_log "
        "(actor_usuario_id, target_usuario_id, target_perfil_id, operacao, recurso, antes, depois, motivo, ip) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (actor_id, target_usuario_id, target_perfil_id, operacao, recurso,
         json.dumps(antes) if antes is not None else None,
         json.dumps(depois) if depois is not None else None, motivo, ip),
    )


def definir_perfis(
    usuario_id: int,
    perfil_ids: list[int],
    *,
    actor_id: int | None = None,
    ip: str | None = None,
) -> None:
    """Substitui os perfis (N:N), validando perfis e último administrador."""
    ids = validar_perfil_ids(perfil_ids, actor_id=actor_id)
    with system_conn() as conn:
        # Serializa mudanças de vínculo para que duas remoções concorrentes
        # não consigam eliminar todos os administradores ativos.
        conn.execute("SELECT pg_advisory_xact_lock(804273)")
        placeholders = ",".join("?" for _ in ids)
        perfil_rows = conn.execute(
            f"SELECT id, nome, ativo FROM perfis WHERE id IN ({placeholders})",
            tuple(ids),
        ).fetchall() if ids else []
        antes = _snapshot_perfis(conn, usuario_id)
        tinha_admin = any(row["nome"] == _PERFIL_ADMIN for row in antes)
        tera_admin = any(row["nome"] == _PERFIL_ADMIN for row in perfil_rows)
        if tinha_admin and not tera_admin:
            ativos_admin = conn.execute(
                "SELECT COUNT(*) AS n FROM usuario_perfis up "
                "JOIN perfis p ON p.id=up.perfil_id "
                "JOIN usuarios u ON u.id=up.usuario_id "
                "WHERE p.nome=? AND p.ativo=1 AND u.ativo=1",
                (_PERFIL_ADMIN,),
            ).fetchone()["n"]
            if int(ativos_admin or 0) <= 1:
                raise ValueError("Não é possível remover o último administrador ativo")
        conn.execute("DELETE FROM usuario_perfis WHERE usuario_id=?", (usuario_id,))
        for pid in ids:
            conn.execute(
                "INSERT INTO usuario_perfis (usuario_id, perfil_id)"
                " VALUES (?,?) ON CONFLICT DO NOTHING",
                (usuario_id, pid),
            )
        depois = _snapshot_perfis(conn, usuario_id)
        _registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=usuario_id,
            operacao="definir_perfis", recurso="usuarios",
            antes=antes, depois=depois, ip=ip,
        )
        conn.commit()
    invalidar(usuario_id)


def definir_overrides(
    usuario_id: int,
    overrides: dict[str, list[str]] | None = None,
    *,
    conceder: dict[str, list[str]] | None = None,
    negar: dict[str, list[str]] | None = None,
    actor_id: int | None = None,
    ip: str | None = None,
) -> None:
    """Substitui os overrides do usuário (concessões e negações por tela).

    Compatível com o payload antigo (`{recurso: [ações]}` = concessões) e com
    o novo (`conceder`/`negar`). Sempre substitui o conjunto inteiro.
    """
    conceder_map = conceder if conceder is not None else (overrides or {})
    negar_map = negar or {}
    validar_overrides_payload(conceder_map, negar_map)
    with system_conn() as conn:
        if actor_id and not _superuser_na_conn(conn, actor_id):
            raise ValueError("Somente um Administrador pode alterar overrides")
        antes = [dict(row) for row in conn.execute(
            "SELECT r.codigo, uo.acoes_extra, uo.acoes_negadas "
            "FROM usuario_override uo JOIN recursos r ON r.id=uo.recurso_id "
            "WHERE uo.usuario_id=? ORDER BY r.codigo", (usuario_id,)
        ).fetchall()]
        recursos = {r["codigo"]: int(r["id"]) for r in conn.execute(
            "SELECT id, codigo FROM recursos"
        ).fetchall()}
        conn.execute("DELETE FROM usuario_override WHERE usuario_id=?", (usuario_id,))
        codigos = set(conceder_map) | set(negar_map)
        for codigo in codigos:
            rid = recursos.get(str(codigo))
            conceder_acoes = conceder_map.get(codigo, [])
            negar_acoes = negar_map.get(codigo, [])
            concedidas = list(dict.fromkeys(conceder_acoes))
            negadas = list(dict.fromkeys(negar_acoes))
            if not concedidas and not negadas:
                continue
            conn.execute(
                "INSERT INTO usuario_override (usuario_id, recurso_id, acoes_extra, acoes_negadas)"
                " VALUES (?,?,?,?)",
                (usuario_id, rid, json.dumps(concedidas), json.dumps(negadas)),
            )
        depois = [dict(row) for row in conn.execute(
            "SELECT r.codigo, uo.acoes_extra, uo.acoes_negadas "
            "FROM usuario_override uo JOIN recursos r ON r.id=uo.recurso_id "
            "WHERE uo.usuario_id=? ORDER BY r.codigo", (usuario_id,)
        ).fetchall()]
        _registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=usuario_id,
            operacao="definir_overrides", recurso="usuarios",
            antes=antes, depois=depois, ip=ip,
        )
        conn.commit()
    invalidar(usuario_id)


def validar_alteracao_ativo(
    actor_id: int | None, usuario_id: int, ativo: bool
) -> None:
    """Impede auto-bloqueio e remoção do último administrador ativo."""
    if not actor_id or not _actor_is_superuser(actor_id):
        raise ValueError("Somente um Administrador pode alterar usuários")
    if ativo:
        return
    with system_conn() as conn:
        if int(actor_id) == int(usuario_id):
            raise ValueError("O usuário logado não pode desativar a própria conta")
        admin = conn.execute(
            "SELECT 1 FROM usuario_perfis up JOIN perfis p ON p.id=up.perfil_id "
            "WHERE up.usuario_id=? AND p.nome=? AND p.ativo=1",
            (usuario_id, _PERFIL_ADMIN),
        ).fetchone()
        if not admin:
            return
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM usuario_perfis up "
            "JOIN perfis p ON p.id=up.perfil_id "
            "JOIN usuarios u ON u.id=up.usuario_id "
            "WHERE p.nome=? AND p.ativo=1 AND u.ativo=1",
            (_PERFIL_ADMIN,),
        ).fetchone()["n"]
        if int(total or 0) <= 1:
            raise ValueError("Não é possível desativar o último administrador ativo")


def alterar_ativo(
    actor_id: int | None,
    usuario_id: int,
    ativo: bool,
    *,
    ip: str | None = None,
) -> bool:
    """Altera o status do usuário com proteção e auditoria na mesma transação."""
    with system_conn() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(804273)")
        if not _superuser_na_conn(conn, actor_id):
            raise ValueError("Somente um Administrador pode alterar usuários")
        atual = conn.execute(
            "SELECT id, nome, login, ativo FROM usuarios WHERE id=?", (usuario_id,)
        ).fetchone()
        if atual is None:
            return False
        if not ativo:
            if int(actor_id) == int(usuario_id):
                raise ValueError("O usuário logado não pode desativar a própria conta")
            admin = conn.execute(
                "SELECT 1 FROM usuario_perfis up JOIN perfis p ON p.id=up.perfil_id "
                "WHERE up.usuario_id=? AND p.nome=? AND p.ativo=1",
                (usuario_id, _PERFIL_ADMIN),
            ).fetchone()
            if admin:
                total = conn.execute(
                    "SELECT COUNT(*) AS n FROM usuario_perfis up "
                    "JOIN perfis p ON p.id=up.perfil_id "
                    "JOIN usuarios u ON u.id=up.usuario_id "
                    "WHERE p.nome=? AND p.ativo=1 AND u.ativo=1",
                    (_PERFIL_ADMIN,),
                ).fetchone()["n"]
                if int(total or 0) <= 1:
                    raise ValueError("Não é possível desativar o último administrador ativo")
        antes = dict(atual)
        conn.execute(
            "UPDATE usuarios SET ativo=?, atualizado_em=datetime('now') WHERE id=?",
            (int(ativo), usuario_id),
        )
        _registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=usuario_id,
            operacao="alternar_usuario", recurso="usuarios",
            antes=antes, depois={**antes, "ativo": bool(ativo)}, ip=ip,
        )
        conn.commit()
    invalidar(usuario_id)
    return True


def _actor_is_superuser(usuario_id: int | None) -> bool:
    return usuario_e_superuser(usuario_id)


def listar_auditoria(limite: int = 200, usuario_id: int | None = None) -> list[dict]:
    """Lista as alterações RBAC mais recentes para investigação administrativa."""
    limite = max(1, min(int(limite or 200), 500))
    where = ""
    params: list = []
    if usuario_id:
        where = " WHERE target_usuario_id=?"
        params.append(usuario_id)
    params.append(limite)
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT id, actor_usuario_id, target_usuario_id, target_perfil_id, "
            "operacao, recurso, antes, depois, motivo, ip, criado_em "
            "FROM rbac_audit_log" + where + " ORDER BY criado_em DESC, id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


# ─── CRUD de perfis (dívida 2) ─────────────────────────────────────────

def criar_perfil(
    nome: str,
    descricao: str = "",
    *,
    actor_id: int | None = None,
    ip: str | None = None,
) -> int:
    """Cria um perfil novo (Administrador é reservado)."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome do perfil")
    if nome == _PERFIL_ADMIN:
        raise ValueError("O perfil Administrador é reservado")
    with system_conn() as conn:
        existente = conn.execute(
            "SELECT 1 FROM perfis WHERE nome=?", (nome,)
        ).fetchone()
        if existente:
            raise ValueError("Já existe um perfil com esse nome")
        cur = conn.execute(
            "INSERT INTO perfis (nome, descricao) VALUES (?,?)",
            (nome, descricao.strip()),
        )
        pid = int(cur.lastrowid)
        _registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=None,
            target_perfil_id=pid, operacao="criar_perfil", recurso="perfis",
            depois={"id": pid, "nome": nome, "descricao": descricao.strip(), "ativo": True},
            ip=ip,
        )
        conn.commit()
    invalidar()
    return pid


def atualizar_perfil(
    perfil_id: int,
    nome: str,
    descricao: str,
    *,
    actor_id: int | None = None,
    ip: str | None = None,
) -> bool:
    """Renomeia/atualiza um perfil (Administrador é reservado)."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome do perfil")
    with system_conn() as conn:
        p = conn.execute(
            "SELECT id, nome, descricao, ativo FROM perfis WHERE id=?", (perfil_id,)
        ).fetchone()
        if p is None:
            return False
        if p["nome"] == _PERFIL_ADMIN:
            raise ValueError("O perfil Administrador é reservado")
        if nome != p["nome"]:
            dup = conn.execute(
                "SELECT 1 FROM perfis WHERE nome=? AND id<>?", (nome, perfil_id)
            ).fetchone()
            if dup:
                raise ValueError("Já existe um perfil com esse nome")
        antes = dict(p)
        conn.execute(
            "UPDATE perfis SET nome=?, descricao=? WHERE id=?",
            (nome, descricao.strip(), perfil_id),
        )
        _registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=None,
            target_perfil_id=perfil_id, operacao="atualizar_perfil", recurso="perfis",
            antes=antes,
            depois={"id": perfil_id, "nome": nome, "descricao": descricao.strip(), "ativo": bool(p["ativo"])},
            ip=ip,
        )
        conn.commit()
    invalidar()
    return True


def set_perfil_ativo(
    perfil_id: int,
    ativo: bool,
    *,
    actor_id: int | None = None,
    ip: str | None = None,
) -> bool:
    """Ativa/desativa um perfil (Administrador nunca é desativado)."""
    with system_conn() as conn:
        p = conn.execute(
            "SELECT id, nome, descricao, ativo FROM perfis WHERE id=?", (perfil_id,)
        ).fetchone()
        if p is None:
            return False
        if p["nome"] == _PERFIL_ADMIN:
            raise ValueError("O perfil Administrador é reservado")
        antes = dict(p)
        conn.execute(
            "UPDATE perfis SET ativo=? WHERE id=?", (1 if ativo else 0, perfil_id)
        )
        _registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=None,
            target_perfil_id=perfil_id, operacao="alternar_perfil", recurso="perfis",
            antes=antes, depois={**antes, "ativo": bool(ativo)}, ip=ip,
        )
        conn.commit()
    invalidar()
    return True


def excluir_perfil(
    perfil_id: int,
    *,
    actor_id: int | None = None,
    ip: str | None = None,
) -> bool:
    """Exclui um perfil. Bloqueia Administrador e perfis em uso por usuários."""
    with system_conn() as conn:
        p = conn.execute(
            "SELECT id, nome, descricao, ativo FROM perfis WHERE id=?", (perfil_id,)
        ).fetchone()
        if p is None:
            return False
        if p["nome"] == _PERFIL_ADMIN:
            raise ValueError("O perfil Administrador é reservado e não pode ser excluído")
        em_uso = conn.execute(
            "SELECT 1 FROM usuario_perfis WHERE perfil_id=? LIMIT 1", (perfil_id,)
        ).fetchone()
        if em_uso:
            raise ValueError("Perfil em uso por usuários — desative-o ou remova os vínculos antes de excluir")
        antes = dict(p)
        conn.execute("DELETE FROM perfis WHERE id=?", (perfil_id,))
        _registrar_auditoria(
            conn, actor_id=actor_id, target_usuario_id=None,
            target_perfil_id=perfil_id, operacao="excluir_perfil", recurso="perfis",
            antes=antes, depois=None, ip=ip,
        )
        conn.commit()
    invalidar()
    return True


def exige_permissao(recurso: str, acao: str):
    """Decorator Flask: bloqueia o endpoint quando o usuário não tem a ação."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            payload = getattr(_request(), "usuario", None)
            usuario_id = payload.get("sub") if payload else None
            if not tem_permissao(usuario_id, recurso, acao):
                abort(403, description=f"Permissão negada: {recurso}.{acao}")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _request():
    from flask import request

    return request


__all__ = [
    "ACOES",
    "tem_permissao",
    "usuario_e_superuser",
    "exige_permissao",
    "usuario_tem_rbac",
    "validar_perfil_ids",
    "validar_overrides_payload",
    "definir_perfis",
    "definir_overrides",
    "criar_perfil",
    "atualizar_perfil",
    "set_perfil_ativo",
    "excluir_perfil",
    "validar_alteracao_ativo",
    "alterar_ativo",
    "listar_auditoria",
    "invalidar",
]
