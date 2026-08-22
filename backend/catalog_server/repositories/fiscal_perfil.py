"""Perfil fiscal do produto (por variante) — skill fiscal-mg §4."""
from __future__ import annotations

from catalog_server.db import system_conn

_CAMPOS = ("ncm", "cest", "origem", "regime_st", "fonte_url")


def obter(variante_id: int) -> dict | None:
    with system_conn() as conn:
        row = conn.execute(
            "SELECT variante_id, ncm, cest, origem, regime_st, fonte_url,"
            " atualizado_em FROM product_fiscal_profile WHERE variante_id=?",
            (variante_id,),
        ).fetchone()
        return dict(row) if row else None


def salvar(variante_id: int, dados: dict) -> dict:
    """Cria/atualiza o perfil validando campos conhecidos."""
    limpo = {k: dados.get(k) for k in _CAMPOS if k in dados}
    limpo["origem"] = int(limpo.get("origem") or 0)
    limpo["ncm"] = (limpo.get("ncm") or "").strip()
    limpo["cest"] = (limpo.get("cest") or "").strip()
    limpo["regime_st"] = (limpo.get("regime_st") or "").strip()
    limpo["fonte_url"] = (limpo.get("fonte_url") or "").strip() or None

    with system_conn() as conn:
        existe = conn.execute(
            "SELECT 1 FROM product_fiscal_profile WHERE variante_id=?",
            (variante_id,),
        ).fetchone()
        if existe:
            sets = ", ".join(f"{k}=?" for k in limpo)
            conn.execute(
                f"UPDATE product_fiscal_profile SET {sets},"
                " atualizado_em=now() WHERE variante_id=?",
                (*limpo.values(), variante_id),
            )
        else:
            cols = ["variante_id", *limpo.keys()]
            conn.execute(
                f"INSERT INTO product_fiscal_profile ({', '.join(cols)})"
                f" VALUES ({', '.join('?' for _ in cols)})",
                (variante_id, *limpo.values()),
            )
        conn.commit()

    return {"variante_id": variante_id, **limpo}


def buscar_ncm(prefixo: str, limite: int = 20) -> list[dict]:
    """Busca NCMs versionados por prefixo do código ou termo da descrição."""
    termo = f"%{(prefixo or '').strip()}%"
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT codigo, descricao, vigencia_inicio, vigencia_fim, fonte_url"
            " FROM ncm_version"
            " WHERE codigo LIKE ? OR descricao ILIKE ?"
            " ORDER BY codigo LIMIT ?",
            (termo + "%", f"%{termo}%", max(1, min(limite, 100))),
        ).fetchall()
        return [dict(r) for r in rows]


def registrar_ncm(dados: dict) -> int:
    """Registra/atualiza um NCM com fonte oficial e vigência (entrada manual
    validada pelo operador — nunca inventado)."""
    codigo = (dados.get("codigo") or "").strip()
    if not codigo:
        raise ValueError("NCM sem código")
    descricao = (dados.get("descricao") or "").strip()
    fonte_url = (dados.get("fonte_url") or "").strip() or None
    vig_ini = (dados.get("vigencia_inicio") or "").strip() or None
    vig_fim = (dados.get("vigencia_fim") or "").strip() or None
    with system_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM ncm_version WHERE codigo=? AND"
            " COALESCE(vigencia_inicio::text,'')=COALESCE(?,'')",
            (codigo, vig_ini),
        ).fetchone()
        if existente:
            conn.execute(
                "UPDATE ncm_version SET descricao=?, fonte_url=? WHERE id=?",
                (descricao, fonte_url, existente["id"]),
            )
            return int(existente["id"])
        cur = conn.execute(
            "INSERT INTO ncm_version (codigo, descricao, fonte_url, vigencia_inicio, vigencia_fim)"
            " VALUES (?,?,?,?,?)",
            (codigo, descricao, fonte_url, vig_ini, vig_fim),
        )
        return int(cur.lastrowid)
