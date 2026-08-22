"""Feature flags do sistema (item 19 do manual — rollback comportamental).

Uso em qualquer blueprint/serviço:

    from catalog_server import flags
    if flags.ativa("NOVO_FLUXO_X"):
        ...

- Leitura em runtime (sem restart): consulta `sistema_flags` com cache em
  processo de ~30s, thread-safe.
- Falha de banco NUNCA derruba o app: retorna o `default` registrado.
- Flags conhecidas ficam no registro `REGISTRADAS` (nome -> descrição) para o
  painel listar; criar uma nova flag = adicionar entrada aqui.
"""
from __future__ import annotations

import threading
import time

from catalog_server.db import system_conn

# Flags conhecidas pelo sistema. Adicione aqui ao introduzir uma nova.
REGISTRADAS: dict[str, str] = {
    # "NOVO_FLUXO_X": "Explica quando usar o caminho novo",
    "FISCAL_ENGINE_V2": (
        "Usa o motor fiscal versionado v2 (regras PUBLISHED por vigência) "
        "para resolver CFOP/CST quando houver regra aplicável"
    ),
}

_TTL = 30.0  # segundos
_lock = threading.Lock()
_cache: dict[str, bool] | None = None
_cache_em: float = 0.0


def _expirado() -> bool:
    return _cache is None or (time.monotonic() - _cache_em) > _TTL


def _carregar() -> dict[str, bool]:
    global _cache, _cache_em
    with _lock:
        if not _expirado():
            return _cache or {}
        estado: dict[str, bool] = {}
        try:
            with system_conn() as conn:
                rows = conn.execute(
                    "SELECT nome, ativo FROM sistema_flags"
                ).fetchall()
            estado = {r["nome"]: bool(r["ativo"]) for r in rows}
        except Exception:
            # Banco indisponível: mantém último cache válido se houver,
            # senão vazio (defaults serão aplicados por ativa()).
            estado = _cache or {}
        _cache = estado
        _cache_em = time.monotonic()
        return estado


def invalidar() -> None:
    """Força recarga na próxima leitura (após definir())."""
    global _cache_em
    with _lock:
        _cache_em = 0.0


def ativa(nome: str, default: bool = False) -> bool:
    """True se a flag estiver ligada; `default` quando ausente ou sem banco."""
    try:
        return bool(_carregar().get(nome, default))
    except Exception:
        return default


def listar() -> list[dict]:
    """Flags registradas com estado atual (do banco ou default False)."""
    estado = _carregar()
    return [
        {
            "nome": nome,
            "descricao": descricao,
            "ativo": bool(estado.get(nome, False)),
        }
        for nome, descricao in REGISTRADAS.items()
    ]


def definir(nome: str, ativo: bool) -> None:
    """Grava o estado da flag e invalida o cache."""
    if nome not in REGISTRADAS:
        raise ValueError(f"flag não registrada: {nome}")
    with system_conn() as conn:
        conn.execute(
            """
            INSERT INTO sistema_flags (nome, ativo, atualizado_em)
            VALUES (?, ?, now())
            ON CONFLICT (nome) DO UPDATE
              SET ativo = EXCLUDED.ativo, atualizado_em = now()
            """,
            (nome, 1 if ativo else 0),
        )
        conn.commit()
    invalidar()
