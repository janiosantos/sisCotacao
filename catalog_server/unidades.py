"""CRUD de unidades de compra predefinidas (`unidades_compra`).

Estas unidades são as opções do campo `unidade_compra` em
`fornecedor_variantes` — o valor digitado no cadastro do produto deve
coincidir com a `sigla` de um registro aqui.
"""
from __future__ import annotations

from catalog_server.db import system_conn


def _clean(value: str) -> str:
    return (value or "").strip().upper()


def listar(apenas_ativas: bool = False) -> list[dict]:
    sql = "SELECT id, sigla, descricao, ativo FROM unidades_compra"
    params: list = []
    if apenas_ativas:
        sql += " WHERE ativo=1"
    sql += " ORDER BY sigla"
    with system_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def obter_por_sigla(sigla: str) -> dict | None:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT id, sigla, descricao, ativo FROM unidades_compra WHERE sigla=?",
            (_clean(sigla),),
        ).fetchone()
    return dict(row) if row else None


def criar(sigla: str, descricao: str) -> tuple[int | None, str]:
    sigla_c = _clean(sigla)
    if not sigla_c:
        return None, "Informe a sigla da unidade"
    with system_conn() as conn:
        existe = conn.execute(
            "SELECT 1 FROM unidades_compra WHERE sigla=?", (sigla_c,)
        ).fetchone()
        if existe:
            return None, f"Unidade '{sigla_c}' já existe"
        cur = conn.execute(
            "INSERT INTO unidades_compra (sigla, descricao, ativo) VALUES (?,?,1)",
            (sigla_c, (descricao or "").strip()),
        )
        return cur.lastrowid, ""


def atualizar(unidade_id: int, sigla: str, descricao: str, ativo: bool) -> tuple[bool, str]:
    sigla_c = _clean(sigla)
    if not sigla_c:
        return False, "Informe a sigla da unidade"
    with system_conn() as conn:
        dup = conn.execute(
            "SELECT 1 FROM unidades_compra WHERE sigla=? AND id<>?",
            (sigla_c, unidade_id),
        ).fetchone()
        if dup:
            return False, f"Unidade '{sigla_c}' já existe"
        cur = conn.execute(
            "UPDATE unidades_compra SET sigla=?, descricao=?, ativo=? WHERE id=?",
            (sigla_c, (descricao or "").strip(), 1 if ativo else 0, unidade_id),
        )
    if cur.rowcount == 0:
        return False, "Unidade não encontrada"
    return True, ""


def excluir(unidade_id: int) -> tuple[bool, str]:
    with system_conn() as conn:
        usada = conn.execute(
            "SELECT 1 FROM fornecedor_variantes WHERE unidade_compra IN"
            " (SELECT sigla FROM unidades_compra WHERE id=?) LIMIT 1",
            (unidade_id,),
        ).fetchone()
        if usada:
            return False, "Unidade já utilizada em códigos de fornecedor"
        cur = conn.execute("DELETE FROM unidades_compra WHERE id=?", (unidade_id,))
    if cur.rowcount == 0:
        return False, "Unidade não encontrada"
    return True, ""