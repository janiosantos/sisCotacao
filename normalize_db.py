"""Normaliza e deduplica a base de produtos do catálogo.

Uso:
    python normalize_db.py            # dry-run (não altera nada)
    python normalize_db.py --apply    # aplica as mudanças + reconstrói o FTS

O que faz:
  1. Deduplicação por EAN real/GTIN (merge): quando o mesmo EAN ocorre em 2+
     produtos, consolida variantes/imagens num único registro (keeper) e
     remapeia cotações. Colisões de NOME NÃO são unidas (SKUs distintos).
  2. Normalização de nomes: Title Case, extrai marca para o campo `marca`
     quando vazio, remove artefatos de título ("VENDIDO POR", hífen final)
     e limpa espaços.
  3. Reconstrói o índice FTS.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from catalog_server.config import DATABASE_URL  # noqa: E402
from catalog_server.db import SYSTEM_DB, system_conn  # noqa: E402

DB = str(SYSTEM_DB)
_IS_PG = bool(DATABASE_URL)


@contextmanager
def _open_db(db_path: str):
    """Conexão do script: shim Postgres (quando configurado) ou SQLite."""
    if _IS_PG:
        with system_conn() as conn:
            yield conn
        return
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Title case / normalização de nomes
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "a", "ao", "aos", "as", "at", "com", "da", "das", "de", "do", "dos",
    "e", "em", "na", "nas", "no", "nos", "num", "numa", "o", "os", "para",
    "por", "sem", "vs",
}
_UNITS = {
    "mm", "cm", "m", "km", "kg", "g", "mg", "ml", "l", "kv", "w", "a", "v",
    "hz", "hp", "un", "pc", "pcs", "rolo", "cm2", "mm2", "m2", "m3",
}
_ACRONYMS = {
    "pvc", "hepr", "eeprm", "eprm", "rj", "led", "lvp", "tv", "nbr",
    "usb", "hdmi", "cd", "esd", "steel", "an", "l", "t",
}
_LETTERS = re.compile(r"[A-Za-z\u00C0-\u00FF]")
_PUNCT_TOKEN = re.compile(r"^[\W_]+$", re.UNICODE)


def smart_title(s: str, whole_upper: bool | None = None) -> str:
    """Converte um título para Title Case preservando acrônimos/unidades."""
    if whole_upper is None:
        letters = "".join(ch for ch in s if ch.isalpha())
        whole_upper = bool(letters) and letters.isupper()
    out: list[str] = []
    for word in s.split():
        if _PUNCT_TOKEN.match(word) or not _LETTERS.search(word):
            out.append(word)
            continue
        if re.search(r"\d", word):  # 750V, 1kV, 90, 1293ES
            out.append(word)
            continue
        low = word.lower()
        if low in _STOPWORDS and not whole_upper:
            out.append(low)
            continue
        if low in _UNITS:
            out.append(low)
            continue
        if low in _ACRONYMS:
            out.append(word.upper() if len(word) > 1 else word)
            continue
        if word.isupper() and len(word) > 1:
            out.append(word.capitalize() if whole_upper else word)
            continue
        out.append(word.capitalize())
    return " ".join(out)


def clean_name(name: str, brand_patterns: list[tuple[str, re.Pattern]]) -> tuple[str, list[str]]:
    """Limpa o nome e devolve marcas identificadas dentro dele.

    Retorna (nome_normalizado, [marcas_encontradas]).
    """
    s = (name or "").strip()
    if not s:
        return s, []
    alpha = "".join(c for c in s if c.isalpha())
    whole_upper = bool(alpha) and alpha.isupper()

    s = re.sub(r"\s*vendido\s+por\b", "", s, flags=re.I)
    s = re.sub(r"\s*[–—-]+\s*$", "", s)
    s = s.strip()

    found: list[str] = []
    for brand, pattern in brand_patterns:
        if pattern.search(s):
            found.append(brand)
            s = pattern.sub(" ", s)

    s = re.sub(r"\s+", " ", s).strip(" -–—")
    s = re.sub(r"\s+([/.),;:!?])", r"\1", s)
    s = re.sub(r"([(/]) ", r"\1", s)
    return smart_title(s, whole_upper), found


def normalize_brand(brand: str | None) -> str:
    b = (brand or "").strip()
    b = re.sub(r"\s+", " ", b)
    if not b:
        return b
    return " ".join(
        w.upper() if w.isupper() and len(w) > 1 else w.capitalize()
        for w in b.split()
    )


# ---------------------------------------------------------------------------
# EAN / GTIN
# ---------------------------------------------------------------------------

def _ean13_check_digit(digits: str) -> int:
    total = sum(int(d) * (1 if i % 2 == 0 else 3)
                for i, d in enumerate(digits[:12]))
    return (10 - (total % 10)) % 10


def real_ean(ean: str | None) -> str | None:
    """EAN/GTIN validado ou None se inválido/placeholder."""
    e = (ean or "").strip()
    if not re.fullmatch(r"\d{8,14}", e):
        return None
    if re.fullmatch(r"\d{1,5}0{6,}", e):  # placeholder 789...0000000
        return None
    if len(e) == 13 and e[-1] == str(_ean13_check_digit(e)):
        return e
    return None


# ---------------------------------------------------------------------------
# Deduplicação (merge por EAN real)
# ---------------------------------------------------------------------------

class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def build_merge_plan(conn) -> list[list[int]]:
    rows = conn.execute(
        "SELECT v.produto_id, v.ean FROM variantes v WHERE TRIM(v.ean)!=''"
    ).fetchall()
    ean_map: dict[str, list[int]] = {}
    for r in rows:
        key = real_ean(r["ean"])
        if key is None:
            continue
        ean_map.setdefault(key, [])
        if r["produto_id"] not in ean_map[key]:
            ean_map[key].append(r["produto_id"])

    prods = {p for ids in ean_map.values() for p in ids}
    pos = {p: i for i, p in enumerate(prods)}
    uf = UnionFind(len(prods))
    for ids in ean_map.values():
        for pid in ids[1:]:
            uf.union(pos[ids[0]], pos[pid])

    comps: dict[int, list[int]] = {}
    for p in prods:
        comps.setdefault(uf.find(pos[p]), []).append(p)

    return [v for v in comps.values() if len(v) > 1]


def pick_keeper(conn, comp: list[int]) -> int:
    rows = conn.execute(
        f"""SELECT p.id, p.ativo,
                   (SELECT COUNT(*) FROM variantes v WHERE v.produto_id=p.id) nv
            FROM produtos_cadastro p WHERE p.id IN ({','.join('?'*len(comp))})""",
        comp,
    ).fetchall()
    return min(rows, key=lambda r: (not r["ativo"], -r["nv"], r["id"]))["id"]


def apply_merge(conn, comp: list[int]) -> dict:
    keeper = pick_keeper(conn, comp)
    losers = [p for p in comp if p != keeper]
    stats = {"losers": losers, "variants": 0, "images": 0, "quotes": 0}
    for loser in losers:
        stats["variants"] += conn.execute(
            "UPDATE variantes SET produto_id=? WHERE produto_id=?", (keeper, loser)
        ).rowcount
        stats["images"] += conn.execute(
            "UPDATE imagens_produto SET produto_id=? WHERE produto_id=?", (keeper, loser)
        ).rowcount
        stats["quotes"] += conn.execute(
            "UPDATE cotacao_itens SET produto_id=? WHERE produto_id=?", (keeper, loser)
        ).rowcount
        conn.execute("DELETE FROM produtos_cadastro WHERE id=?", (loser,))
    return stats


# ---------------------------------------------------------------------------
# Normalização em massa
# ---------------------------------------------------------------------------

def load_brands(conn) -> set[str]:
    out: set[str] = set()
    for (b,) in conn.execute(
        "SELECT DISTINCT marca FROM produtos_cadastro WHERE TRIM(marca)!=''"
    ):
        for piece in re.split(r"[|/,]", b or ""):
            piece = piece.strip()
            if 3 <= len(piece) <= 24 and not piece.isdigit():
                out.add(piece)
    return out


# ---------------------------------------------------------------------------
# Colisões de nome (mesmo nome + família + marca)
# ---------------------------------------------------------------------------

def _attr_sig(conn, pid: int) -> tuple:
    at = conn.execute(
        """SELECT fa.nome || '\x1f' || va.valor s FROM variante_atributos va
           JOIN familia_atributos fa ON fa.id = va.atributo_id
           JOIN variantes v ON v.id = va.variante_id WHERE v.produto_id = ?
           ORDER BY s""",
        (pid,),
    ).fetchall()
    return tuple(a["s"] for a in at)


def build_collision_plan(conn) -> tuple[list[list[int]], list[tuple]]:
    """Separa grupos colidentes em (para-merge, para-diferenciar-nome)."""
    rows = conn.execute(
        """SELECT LOWER(nome) n, familia_id f, LOWER(marca) m,
                  GROUP_CONCAT(id) ids
           FROM produtos_cadastro
           GROUP BY LOWER(nome), familia_id, LOWER(marca)
           HAVING COUNT(*)>1"""
    ).fetchall()
    to_merge: list[list[int]] = []
    to_diff: list[tuple] = []
    for g in rows:
        idlist = [int(x) for x in g["ids"].split(",")]
        sigs = {_attr_sig(conn, p) for p in idlist}
        if not any(sigs):
            # sem atributos: merge apenas se houver EAN compartilhado
            eans = [
                {r["ean"] for r in conn.execute(
                    "SELECT ean FROM variantes WHERE produto_id=? AND TRIM(ean)!=''", (p,))}
                for p in idlist
            ]
            shared = any(eans[i] & eans[j]
                         for i in range(len(eans)) for j in range(i + 1, len(eans)))
            if shared:
                to_merge.append(idlist)
            else:
                to_diff.append((g["n"], idlist))
        else:
            to_merge.append(idlist)  # variação ou duplicata
    return to_merge, to_diff


def _slug_tokens(conn, pid: int) -> list[str]:
    u = conn.execute("SELECT url FROM produtos_cadastro WHERE id=?", (pid,)).fetchone()["url"] or ""
    if "/produto/" in u:
        slug = u.split("/produto/", 1)[1].split("?")[0]
    else:
        slug = u.split("/")[-1].split("?")[0]
    return [t for t in re.split(r"[-_]", slug) if t]


def disambiguate_names(conn, to_diff: list[tuple]) -> int:
    """Anexa um discriminador (slug/código da loja) a nomes colidentes."""
    n = 0
    for gname, idlist in to_diff:
        toks_map: dict[int, list[str]] = {}
        common: set[str] | None = None
        for pid in idlist:
            t = _slug_tokens(conn, pid)
            toks_map[pid] = t
            common = set(t) if common is None else (common & set(t))
        for pid in idlist:
            uniq = [x for x in toks_map[pid] if x not in (common or set())]
            meaningful = [x for x in uniq if not x.isdigit()]
            disc = " ".join(meaningful) or " ".join(uniq)
            if not disc:
                sku = conn.execute(
                    "SELECT sku FROM variantes WHERE produto_id=? AND TRIM(sku)!='' LIMIT 1",
                    (pid,),
                ).fetchone()
                disc = sku["sku"] if sku else None
            if disc:
                nome = conn.execute("SELECT nome FROM produtos_cadastro WHERE id=?", (pid,)).fetchone()["nome"]
                conn.execute(
                    "UPDATE produtos_cadastro SET nome=?, atualizado_em=datetime('now') WHERE id=?",
                    (f"{nome} - {disc}", pid),
                )
                n += 1
    return n


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Normaliza/deduplica a base.")
    parser.add_argument("--apply", action="store_true", help="Aplica (dry-run por padrão).")
    parser.add_argument("--db", default=DB)
    args = parser.parse_args()

    with _open_db(args.db) as conn:
        _main(conn, args)


def _main(conn, args) -> None:
    brands = load_brands(conn)
    print(f"marcas conhecidas: {len(brands)}")
    brand_patterns = [(b, re.compile(rf"\b{re.escape(b)}\b", re.I))
                      for b in sorted(brands, key=len, reverse=True)]

    # ---------- 1. DEDUP ----------
    comps = build_merge_plan(conn)
    n_losers = sum(len(c) - 1 for c in comps)
    loser_set = {p for c in comps for p in c[1:]}
    n_quotes = 0
    if loser_set:
        n_quotes = conn.execute(
            f"SELECT COUNT(*) n FROM cotacao_itens WHERE produto_id IN ({','.join('?'*len(loser_set))})",
            list(loser_set),
        ).fetchone()["n"]

    print(f"\n== DEDUP por EAN real ==\ngrupos: {len(comps)} | excedentes a remover: {n_losers} | cotações remapeadas: {n_quotes}")
    for c in sorted(comps, key=len, reverse=True)[:8]:
        eans = sorted({real_ean(r["ean"]) for r in conn.execute(
            "SELECT ean FROM variantes WHERE produto_id IN (%s)" % ",".join("?"*len(c)), c)})
        print(f"   {c} -> EANs {eans}")

    # ---------- 2. NOMES ----------
    print("\n== NORMALIZAÇÃO de nomes == (amostra antes -> depois)")
    changed = 0
    brand_fill = 0
    samples: list[tuple] = []
    for r in conn.execute("SELECT id, nome, marca FROM produtos_cadastro"):
        new_name, found = clean_name(r["nome"], brand_patterns)
        name_changed = new_name != (r["nome"] or "")
        fill = bool(found) and not (r["marca"] or "").strip()
        if name_changed or fill:
            changed += 1
            if fill:
                brand_fill += 1
            if len(samples) < 15:
                samples.append((r["id"], r["nome"], new_name, found, fill))
    for pid, before, after, found, fill in samples:
        extra = f" +marca:{','.join(found)}" if fill else ""
        print(f"   [{pid}] {before[:62]}")
        print(f"        -> {after[:62]}{extra}")
    print(f"produtos com nome alterado: {changed}  (marca extraída: {brand_fill})")

    # ---------- 2.5. COLISÕES DE NOME ----------
    print("\n== COLISÕES de nome (mesmo nome+família+marca) ==")
    to_merge, to_diff = build_collision_plan(conn)
    n_exc = sum(len(c) - 1 for c in to_merge)
    n_diff = sum(len(ids) for _, ids in to_diff)
    print(f"grupos para merge: {len(to_merge)} (pais excedentes: {n_exc})")
    print(f"grupos a diferenciar por código: {len(to_diff)} (produtos: {n_diff})")
    print("amostra de merge (pai terá variantes):")
    for c in sorted(to_merge, key=len, reverse=True)[:4]:
        print(f"   ids {c} | sigs=", {_attr_sig(conn, p) for p in c})
    print("amostra de diferenciação:")
    for gname, ids in to_diff[:5]:
        for pid in ids:
            uniq = _slug_tokens(conn, pid)
            print(f"   [{pid}] '{gname[:40]}' -> tokens {uniq}")
        print()

    if not args.apply:
        print("\n[dry-run] Nada foi alterado. Rode com --apply para aplicar.")
        return

    # ---------- 3. APLICA ----------
    print("\n== APLICANDO ==")
    stats = {"deleted": 0, "variants": 0, "images": 0, "quotes": 0}
    try:
        for c in comps:
            st = apply_merge(conn, c)
            stats["deleted"] += len(st["losers"])
            stats["variants"] += st["variants"]
            stats["images"] += st["images"]
            stats["quotes"] += st["quotes"]

        n_name = 0
        for r in conn.execute("SELECT id, nome, marca FROM produtos_cadastro"):
            new_name, found = clean_name(r["nome"], brand_patterns)
            new_marca = r["marca"] or ""
            if found and not new_marca.strip():
                new_marca = normalize_brand(found[0])
            if new_name != (r["nome"] or "") or new_marca != (r["marca"] or ""):
                conn.execute(
                    "UPDATE produtos_cadastro SET nome=?, marca=?, atualizado_em=datetime('now') WHERE id=?",
                    (new_name, new_marca, r["id"]),
                )
                n_name += 1

        # colisões de nome
        n_coll = 0
        n_disamb = 0
        for c in to_merge:
            st = apply_merge(conn, c)
            stats["deleted"] += len(st["losers"])
            stats["variants"] += st["variants"]
            stats["images"] += st["images"]
            stats["quotes"] += st["quotes"]
            n_coll += 1
        n_disamb = disambiguate_names(conn, to_diff)

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    # ---------- 4. FTS ----------
    from catalog_server import fts
    fts.ensure_fts(conn)
    fts.rebuild(conn)
    conn.commit()
    n_prod = conn.execute("SELECT COUNT(*) n FROM produtos_cadastro").fetchone()["n"]
    n_fts = conn.execute("SELECT COUNT(*) n FROM produtos_fts").fetchone()["n"]
    print(f"produtos restantes: {n_prod} | índice FTS: {n_fts}")
    print("merge:", stats)
    print(f"nomes normalizados: {n_name} | colisões unidas: {n_coll} | nomes diferenciados: {n_disamb}")


if __name__ == "__main__":
    main()
