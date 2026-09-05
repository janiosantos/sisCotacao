"""Identificadores m�ltiplos de produto (MDM-003).

EAN/GTIN, c�digo interno, c�digo do fabricante, do fornecedor e de embalagem,
com valida����o GTIN e busca exata (antes da busca textual). Apenas Expand: n�o
altera o contrato atual (`produtos_cadastro.ean`/`sku` continuam como fonte
legada de leitura).
"""

from __future__ import annotations

from catalog_server.db import system_conn

TIPOS_VALIDOS = {"ean", "gtin", "codigo_interno", "fabricante", "fornecedor", "embalagem"}
_TIPOS_DIGITO = {"ean", "gtin"}

_COLUNAS = (
    "id, produto_id, tipo, valor, embalagem, origem, ativo, criado_em, atualizado_em"
)


def normalizar_valor(tipo: str, valor: str) -> str:
    v = (valor or "").strip()
    if tipo in _TIPOS_DIGITO:
        v = "".join(ch for ch in v if ch.isdigit())
        if v and len(v) not in (8, 12, 13, 14):
            raise ValueError("GTIN/EAN deve ter 8, 12, 13 ou 14 d�gitos")
    return v


def listar(produto_id: int) -> list[dict]:
    with system_conn() as conn:
        rows = conn.execute(
            f"SELECT {_COLUNAS} FROM produto_identificador "
            "WHERE produto_id=? AND ativo ORDER BY tipo, valor",
            (produto_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def salvar(
    produto_id: int,
    tipo: str,
    valor: str,
    embalagem: str | None,
    origem: str | None,
    usuario_id: int | None,
) -> dict:
    tipo = (tipo or "").strip().lower()
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo inv�lido: {tipo}")
    v = normalizar_valor(tipo, valor)
    if not v:
        raise ValueError("informe o valor do identificador")
    emb = (embalagem or "").strip().upper() or None
    if tipo == "embalagem" and not emb:
        raise ValueError("tipo 'embalagem' exige a embalagem")
    with system_conn() as conn:
        ativo = conn.execute(
            "SELECT id FROM produto_identificador "
            "WHERE produto_id=? AND tipo=? AND valor=? AND ativo",
            (produto_id, tipo, v),
        ).fetchone()
        if ativo:
            # J� ativo com o mesmo valor: apenas atualiza metadados opcionais.
            conn.execute(
                "UPDATE produto_identificador SET embalagem=?, atualizado_em=NOW() WHERE id=?",
                (emb, ativo["id"]),
            )
            novo_id = ativo["id"]
        else:
            novo_id = conn.execute(
                "INSERT INTO produto_identificador "
                "(produto_id, tipo, valor, embalagem, origem, ativo, criado_por) "
                "VALUES (?,?,?,?,?,TRUE,?) RETURNING id",
                (produto_id, tipo, v, emb, (origem or "manual").strip()[:20] or "manual", usuario_id),
            ).fetchone()["id"]
        r = conn.execute(
            f"SELECT {_COLUNAS} FROM produto_identificador WHERE id=?",
            (novo_id,),
        ).fetchone()
        return dict(r)


def excluir(produto_id: int, identificador_id: int) -> bool:
    with system_conn() as conn:
        cur = conn.execute(
            "UPDATE produto_identificador SET ativo=FALSE, atualizado_em=NOW() "
            "WHERE id=? AND produto_id=? AND ativo",
            (identificador_id, produto_id),
        )
        return cur.rowcount > 0


def buscar(termo: str, limite: int = 20) -> list[dict]:
    """Busca exata por c�digo (identificador ativo, ean ou sku legados)."""
    termo = (termo or "").strip()
    if not termo:
        return []
    termo_digits = "".join(ch for ch in termo if ch.isdigit())
    termo_gtin = termo_digits if len(termo_digits) in (8, 12, 13, 14) else "__SEM_GTIN__"
    limite = min(max(limite, 1), 100)
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT p.id, p.nome, p.sku, p.ean
            FROM (
                SELECT produto_id FROM produto_identificador
                WHERE ativo AND (valor ILIKE ? OR valor=?)
                UNION ALL
                SELECT id AS produto_id FROM produtos_cadastro WHERE ean=?
                UNION ALL
                SELECT id AS produto_id FROM produtos_cadastro WHERE sku ILIKE ?
            ) t
            JOIN produtos_cadastro p ON p.id=t.produto_id
            WHERE p.ativo=1
            ORDER BY p.nome
            LIMIT ?
            """,
            (termo, termo_gtin, termo_gtin, termo, limite),
        ).fetchall()
        return [dict(r) for r in rows]
