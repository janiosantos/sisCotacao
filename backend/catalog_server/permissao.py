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

_ACOES = ("visualizar", "cadastrar", "editar", "excluir", "imprimir", "aprovar", "configurar")

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
            " WHERE up.usuario_id=? AND p.nome=?",
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


# ─── Gravação da relação RBAC (usada por api_usuarios e api_permissoes) ───

def definir_perfis(usuario_id: int, perfil_ids: list[int]) -> None:
    """Substitui os perfis (N:N) do usuário."""
    with system_conn() as conn:
        conn.execute("DELETE FROM usuario_perfis WHERE usuario_id=?", (usuario_id,))
        for pid in perfil_ids:
            conn.execute(
                "INSERT INTO usuario_perfis (usuario_id, perfil_id)"
                " SELECT ?, id FROM perfis WHERE id=? AND ativo=1"
                " ON CONFLICT DO NOTHING",
                (usuario_id, int(pid)),
            )
        conn.commit()
    invalidar(usuario_id)


def definir_overrides(
    usuario_id: int,
    overrides: dict[str, list[str]] | None = None,
    *,
    conceder: dict[str, list[str]] | None = None,
    negar: dict[str, list[str]] | None = None,
) -> None:
    """Substitui os overrides do usuário (concessões e negações por tela).

    Compatível com o payload antigo (`{recurso: [ações]}` = concessões) e com
    o novo (`conceder`/`negar`). Sempre substitui o conjunto inteiro.
    """
    conceder_map = conceder if conceder is not None else (overrides or {})
    negar_map = negar or {}
    with system_conn() as conn:
        recursos = {r["codigo"]: int(r["id"]) for r in conn.execute(
            "SELECT id, codigo FROM recursos"
        ).fetchall()}
        conn.execute("DELETE FROM usuario_override WHERE usuario_id=?", (usuario_id,))
        codigos = set(conceder_map) | set(negar_map)
        for codigo in codigos:
            rid = recursos.get(str(codigo))
            if rid is None:
                continue
            concedidas = [a for a in conceder_map.get(codigo, []) if a in _ACOES]
            negadas = [a for a in negar_map.get(codigo, []) if a in _ACOES]
            if not concedidas and not negadas:
                continue
            conn.execute(
                "INSERT INTO usuario_override (usuario_id, recurso_id, acoes_extra, acoes_negadas)"
                " VALUES (?,?,?,?)",
                (usuario_id, rid, json.dumps(concedidas), json.dumps(negadas)),
            )
        conn.commit()
    invalidar(usuario_id)


# ─── CRUD de perfis (dívida 2) ─────────────────────────────────────────

def criar_perfil(nome: str, descricao: str = "") -> int:
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
        conn.commit()
    invalidar()
    return pid


def atualizar_perfil(perfil_id: int, nome: str, descricao: str) -> bool:
    """Renomeia/atualiza um perfil (Administrador é reservado)."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome do perfil")
    with system_conn() as conn:
        p = conn.execute(
            "SELECT nome FROM perfis WHERE id=?", (perfil_id,)
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
        conn.execute(
            "UPDATE perfis SET nome=?, descricao=? WHERE id=?",
            (nome, descricao.strip(), perfil_id),
        )
        conn.commit()
    invalidar()
    return True


def set_perfil_ativo(perfil_id: int, ativo: bool) -> bool:
    """Ativa/desativa um perfil (Administrador nunca é desativado)."""
    with system_conn() as conn:
        p = conn.execute(
            "SELECT nome FROM perfis WHERE id=?", (perfil_id,)
        ).fetchone()
        if p is None:
            return False
        if p["nome"] == _PERFIL_ADMIN:
            raise ValueError("O perfil Administrador é reservado")
        conn.execute(
            "UPDATE perfis SET ativo=? WHERE id=?", (1 if ativo else 0, perfil_id)
        )
        conn.commit()
    invalidar()
    return True


def excluir_perfil(perfil_id: int) -> bool:
    """Exclui um perfil. Bloqueia Administrador e perfis em uso por usuários."""
    with system_conn() as conn:
        p = conn.execute(
            "SELECT nome FROM perfis WHERE id=?", (perfil_id,)
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
        conn.execute("DELETE FROM perfis WHERE id=?", (perfil_id,))
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
    "exige_permissao",
    "usuario_tem_rbac",
    "definir_perfis",
    "definir_overrides",
    "criar_perfil",
    "atualizar_perfil",
    "set_perfil_ativo",
    "excluir_perfil",
    "invalidar",
]