"""Sugestão automática de NCM a partir da descrição IBPT (por nome do produto).

Casa os tokens significativos do nome/marca do produto com as descrições da
tabela `ibpt` (índice invertido) e gera, para cada variante sem NCM, uma
sugestão com confiança (cobertura dos tokens do produto na descrição IBPT).

As sugestões ficam em `ibpt_sugestoes` (status `pendente`) para revisão;
`aplicar` só então grava `variantes.ncm` e propaga para `fiscal_config.ncm`.
"""
from __future__ import annotations

import unicodedata
from collections import defaultdict

from catalog_server.db import system_conn

_CONFIANCA_MIN = 40.0


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return "".join(c.lower() if c.isalnum() else " " for c in texto)


def tokens(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if len(t) >= 3]


def gerar_sugestoes(limite: int | None = None, confianca_min: float | None = None) -> dict:
    conf_min = confianca_min if confianca_min is not None else _CONFIANCA_MIN
    with system_conn() as conn:
        ibpt = [dict(r) for r in conn.execute(
            "SELECT ncm, descricao FROM ibpt WHERE descricao != ''"
        ).fetchall()]
    ibpt_toks = [set(tokens(r["descricao"])) for r in ibpt]

    # índice invertido: token → índices dos registros IBPT que o contêm
    idx: dict[str, list[int]] = defaultdict(list)
    for i, tks in enumerate(ibpt_toks):
        for t in tks:
            idx[t].append(i)

    with system_conn() as conn:
        produtos = [dict(r) for r in conn.execute(
            "SELECT v.id AS variante_id, p.nome, p.marca"
            " FROM variantes v JOIN produtos_cadastro p ON p.id=v.produto_id"
            " WHERE v.ativo=1 AND (v.ncm IS NULL OR v.ncm='')"
        ).fetchall()]

    sugestoes = []
    for prod in produtos:
        pts = tokens((prod["nome"] or "") + " " + (prod["marca"] or ""))
        if not pts:
            continue
        pts_set = set(pts)
        # candidatos = registros do token MAIS RARO do produto (menor postagem)
        rarest = min((t for t in pts_set if t in idx), key=lambda t: len(idx[t]), default=None)
        if rarest is None:
            continue
        melhor: tuple[float, int, int] | None = None
        for i in idx[rarest]:
            cobertos = len(pts_set & ibpt_toks[i])
            if cobertos == 0:
                continue
            # confiança bilateral: a categoria IBPT deve ser coberta pelo
            # produto E a categoria deve ser parte relevante do nome.
            ib_cob = cobertos / len(ibpt_toks[i])
            pr_cob = cobertos / len(pts_set)
            conf = min(ib_cob, pr_cob)
            candidato = (conf, cobertos, i)
            if melhor is None or candidato > melhor:
                melhor = candidato
        if melhor is None:
            continue
        conf, cobertos, ib = melhor
        conf = round(conf * 100, 1)
        if conf < conf_min:
            continue
        sugestoes.append((prod["variante_id"], ibpt[ib]["ncm"], ibpt[ib]["descricao"], conf))
        if limite and len(sugestoes) >= limite:
            break

    if sugestoes:
        with system_conn() as conn:
            conn.executemany(
                "INSERT INTO ibpt_sugestoes (variante_id, ncm, descricao, confianca, status)"
                " VALUES (?,?,?,?,'pendente')"
                " ON CONFLICT(variante_id) DO UPDATE SET"
                " ncm=excluded.ncm, descricao=excluded.descricao,"
                " confianca=excluded.confianca, status='pendente'",
                sugestoes,
            )
    return {"sugestoes": len(sugestoes), "confianca_min": conf_min, "total_produtos": len(produtos)}


def _aplicar_uma(conn, variante_id: int, ncm: str) -> None:
    conn.execute("UPDATE variantes SET ncm=? WHERE id=?", (ncm, variante_id))
    # propaga para fiscal_config (mesma conexão, sem aninhar)
    if conn.execute("SELECT 1 FROM fiscal_config WHERE variante_id=?", (variante_id,)).fetchone():
        conn.execute("UPDATE fiscal_config SET ncm=? WHERE variante_id=?", (ncm, variante_id))
    else:
        conn.execute("INSERT INTO fiscal_config (variante_id, ncm) VALUES (?,?)", (variante_id, ncm))


def aplicar(confianca_min: float | None = None) -> dict:
    conf_min = confianca_min if confianca_min is not None else 0.0
    with system_conn() as conn:
        pendentes = [dict(r) for r in conn.execute(
            "SELECT id, variante_id, ncm FROM ibpt_sugestoes"
            " WHERE status='pendente' AND confianca >= ?",
            (conf_min,),
        ).fetchall()]
        for s in pendentes:
            _aplicar_uma(conn, s["variante_id"], s["ncm"])
            conn.execute(
                "UPDATE ibpt_sugestoes SET status='aplicada', aplicado_em=datetime('now') WHERE id=?",
                (s["id"],),
            )
        return {"aplicadas": len(pendentes)}


def aplicar_uma(sugestao_id: int) -> bool:
    with system_conn() as conn:
        s = conn.execute(
            "SELECT variante_id, ncm FROM ibpt_sugestoes WHERE id=? AND status='pendente'",
            (sugestao_id,),
        ).fetchone()
        if s is None:
            return False
        _aplicar_uma(conn, s["variante_id"], s["ncm"])
        conn.execute(
            "UPDATE ibpt_sugestoes SET status='aplicada', aplicado_em=datetime('now') WHERE id=?",
            (sugestao_id,),
        )
        return True


def resumo_categorias(limite: int = 200) -> list[dict]:
    """NCM mais sugerido por subcategoria (revisão em massa)."""
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.subcategoria_id, COALESCE(sub.nome,'') AS subcategoria,
                   s.ncm, i.descricao AS descricao_ibpt,
                   COUNT(*) AS n_produtos,
                   ROUND(AVG(s.confianca),1) AS confianca_media
            FROM ibpt_sugestoes s
            JOIN variantes v ON v.id=s.variante_id
            JOIN produtos_cadastro p ON p.id=v.produto_id
            LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id
            LEFT JOIN ibpt i ON i.ncm=s.ncm
            WHERE s.status='pendente'
            GROUP BY p.subcategoria_id, s.ncm
            ORDER BY n_produtos DESC, confianca_media DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
        out: list[dict] = []
        visto: set[int] = set()
        for r in rows:
            sid = r["subcategoria_id"]
            if sid in visto:
                continue
            visto.add(sid)
            out.append({
                "subcategoria_id": sid,
                "subcategoria": r["subcategoria"],
                "ncm": r["ncm"],
                "descricao_ibpt": r["descricao_ibpt"] or "",
                "n_produtos": r["n_produtos"],
                "confianca_media": r["confianca_media"],
            })
        return out


def aplicar_por_categoria(subcategoria_id: int, ncm: str) -> dict:
    """Aplica um NCM a todas as variantes ativas sem NCM de uma subcategoria."""
    ncm = (ncm or "").strip()
    if not ncm or not ncm.isdigit():
        return {"aplicados": 0, "erro": "NCM inválido"}
    with system_conn() as conn:
        vids = [r["id"] for r in conn.execute(
            "SELECT v.id FROM variantes v"
            " JOIN produtos_cadastro p ON p.id=v.produto_id"
            " WHERE p.subcategoria_id=? AND v.ativo=1 AND (v.ncm IS NULL OR v.ncm='')",
            (subcategoria_id,),
        ).fetchall()]
        for vid in vids:
            _aplicar_uma(conn, vid, ncm)
        if vids:
            ph = ", ".join("?" for _ in vids)
            conn.execute(
                f"UPDATE ibpt_sugestoes SET status='aplicada', aplicado_em=datetime('now')"
                f" WHERE variante_id IN ({ph}) AND ncm=?",
                vids + [ncm],
            )
        return {"aplicados": len(vids)}
