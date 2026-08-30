"""Rate limit distribuído para autenticação."""
from __future__ import annotations

import hashlib
import os
import time

from catalog_server.db import system_conn


def _limite() -> int:
    return max(1, int(os.getenv("LOGIN_RATE_LIMIT", "5")))


def _janela() -> int:
    return max(30, int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "300")))


def _hash(chave: str) -> str:
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


def _chaves(ip: str, login: str) -> tuple[str, str]:
    # Limita simultaneamente por origem e por conta, evitando que um atacante
    # teste muitos logins a partir do mesmo IP ou uma conta a partir de vários IPs.
    return _hash(f"ip:{ip}"), _hash(f"login:{login or '<vazio>'}")


def permitir(ip: str, login: str) -> bool:
    agora = int(time.time())
    janela = _janela()
    limite = _limite()
    chaves = _chaves(ip, login)
    with system_conn() as conn:
        rows = {
            row["chave_hash"]: row
            for row in conn.execute(
                "SELECT chave_hash, janela_inicio, tentativas "
                "FROM login_rate_limit WHERE chave_hash IN (?, ?) FOR UPDATE",
                chaves,
            ).fetchall()
        }
        bloqueado = False
        for chave in chaves:
            row = rows.get(chave)
            if not row or agora - int(row["janela_inicio"]) >= janela:
                conn.execute(
                    "INSERT INTO login_rate_limit "
                    "(chave_hash, janela_inicio, tentativas) VALUES (?, ?, 1) "
                    "ON CONFLICT (chave_hash) DO UPDATE SET "
                    "janela_inicio=EXCLUDED.janela_inicio, tentativas=1, atualizado_em=NOW()",
                    (chave, agora),
                )
            elif int(row["tentativas"]) >= limite:
                bloqueado = True
            else:
                conn.execute(
                    "UPDATE login_rate_limit SET tentativas=tentativas+1, "
                    "atualizado_em=NOW() WHERE chave_hash=?",
                    (chave,),
                )
        return not bloqueado


def limpar(ip: str, login: str) -> None:
    chaves = _chaves(ip, login)
    with system_conn() as conn:
        conn.execute(
            "DELETE FROM login_rate_limit WHERE chave_hash IN (?, ?)", chaves
        )


def limpar_expiradas() -> int:
    """Remove janelas antigas; pode ser chamado por manutenção periódica."""
    corte = int(time.time()) - (_janela() * 2)
    with system_conn() as conn:
        cur = conn.execute(
            "DELETE FROM login_rate_limit WHERE janela_inicio < ?", (corte,)
        )
        return cur.rowcount
