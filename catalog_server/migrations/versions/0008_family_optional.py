"""0008 — Família opcional, limpeza de atributos e extração de códigos.

Mudanças:
1. `familia_id` em `produtos_cadastro` passa a ser OPCIONAL (NULL = produto simples)
2. Atributos de `Bitola / Tamanho` limpos (só valores de bitola de fio, não parafuso)
3. Códigos no início do nome (ex: "1524 Termômetro") extraídos para external_id
4. Famílias duplicadas/vazias (Lampada, Lâmpadas) removidas
5. "Importados" esvaziado: produtos sem variações viram simples (familia_id=NULL)
6. Atributo "Diâmetro" removido de Cabo Flexível (redundante com Bitola/Tamanho)
"""
from __future__ import annotations

import re
import sqlite3

VERSION = 8
NAME = "Família opcional + limpeza de atributos"

# Atributos que devem ser removidos (redundantes/confusos)
ATRIBUTOS_REMOVER = [
    ("Cabo Flexível", "Diâmetro"),
]

# Padrão para códigos no INÍCIO do nome: "1524 Termômetro..." → código "1524"
PADRAO_CODIGO_INICIO = re.compile(r"^(\d+[-.\w]*)\s+")

# Valores de "Bitola / Tamanho" que SÃO bitola de fio (mm² ou mm com contexto de cabo)
RE_BITOLA_FIO = re.compile(
    r"^\d+[.,]?\d*\s*mm²$|^\d+x\d+[.,]?\d*\s*mm²$|"
    r"^\d+[.,]?\d*\s*MM2$",
    re.IGNORECASE,
)

# Famílias duplicadas/vazias para remover
FAMILIAS_REMOVER = {14: "Lampada", 26: "Lâmpadas"}

# Família Importados (32) — será esvaziada
ID_IMPORTADOS = 32


def _extrair_codigo_inicio(nome: str) -> tuple[str, str | None]:
    m = PADRAO_CODIGO_INICIO.match(nome)
    if m:
        cod = m.group(1).strip()
        nome_resto = nome[m.end():].strip()
        if len(cod) >= 3 and re.search(r"\d", cod):
            return nome_resto, cod
    return nome, None


def guard(conn: sqlite3.Connection) -> bool:
    """Já aplicada se produtos_cadastro permite familia_id NULL."""
    cols = {r[1]: r for r in conn.execute("PRAGMA table_info(produtos_cadastro)").fetchall()}
    col = cols.get("familia_id")
    return col is not None and not col[3]  # col[3] = notnull (0 = nullable)


def forward(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN")
    try:
        # ---- 1. Extrair códigos do início do nome ----
        for r in conn.execute(
            "SELECT id, nome, external_id FROM produtos_cadastro WHERE nome GLOB '[0-9]*'"
        ).fetchall():
            pid, nome, ext_atual = r[0], r[1], r[2]
            nome_limpo, codigo = _extrair_codigo_inicio(nome)
            if codigo and nome_limpo != nome:
                ext_final = codigo if not ext_atual else str(ext_atual or "")
                conn.execute(
                    "UPDATE produtos_cadastro SET nome=?, external_id=?, atualizado_em=datetime('now') WHERE id=?",
                    (nome_limpo, ext_final, pid),
                )

        # ---- 2. Remover atributos redundantes ----
        for fam_nome, attr_nome in ATRIBUTOS_REMOVER:
            conn.execute(
                "DELETE FROM familia_atributos WHERE familia_id=(SELECT id FROM familias WHERE nome=?) AND nome=?",
                (fam_nome, attr_nome),
            )

        # ---- 3. Limpar opções de Bitola / Tamanho (só bitola de fio) ----
        cabofid = conn.execute("SELECT id FROM familias WHERE nome='Cabo Flexível'").fetchone()
        if cabofid:
            fid = cabofid[0]
            row = conn.execute(
                "SELECT id, opcoes FROM familia_atributos WHERE familia_id=? AND nome='Bitola / Tamanho'",
                (fid,),
            ).fetchone()
            if row:
                import json
                try:
                    opcoes = json.loads(row[1]) if row[1] else []
                except (json.JSONDecodeError, TypeError):
                    opcoes = []
                filtradas = [o for o in opcoes if isinstance(o, str) and RE_BITOLA_FIO.match(o)]
                conn.execute(
                    "UPDATE familia_atributos SET opcoes=? WHERE id=?",
                    (json.dumps(filtradas, ensure_ascii=False), row[0]),
                )

        # ---- 4. Schema: reconstruir produtos_cadastro com familia_id opcional ----
        conn.execute("""
            CREATE TABLE produtos_cadastro_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                familia_id INTEGER REFERENCES familias(id),
                nome TEXT NOT NULL,
                marca TEXT DEFAULT '',
                descricao TEXT DEFAULT '',
                categoria_id INTEGER REFERENCES categorias(id),
                subcategoria_id INTEGER REFERENCES subcategorias(id),
                termos_busca TEXT DEFAULT '',
                embalagem TEXT DEFAULT '',
                url TEXT DEFAULT '',
                external_id INTEGER,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                atualizado_em TEXT,
                linha_produto TEXT DEFAULT '',
                classe_abc TEXT DEFAULT '',
                ordem_abc INTEGER DEFAULT 0,
                margem_lucro_estimada REAL,
                giro_esperado_mercado REAL,
                valor_agregado TEXT DEFAULT '',
                lucro_total_estimado REAL,
                em_linha INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            INSERT INTO produtos_cadastro_new SELECT * FROM produtos_cadastro
        """)
        conn.execute("DROP TABLE produtos_cadastro")
        conn.execute("ALTER TABLE produtos_cadastro_new RENAME TO produtos_cadastro")

        # ---- 5. Recriar índices ----
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos_cadastro(nome COLLATE NOCASE)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_familia ON produtos_cadastro(familia_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_categoria_id ON produtos_cadastro(categoria_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_subcategoria_id ON produtos_cadastro(subcategoria_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_ativo ON produtos_cadastro(ativo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_em_linha ON produtos_cadastro(em_linha)")

        # ---- 6. Famílias duplicadas: migrar produtos de Lampada (14) para Lâmpada (15) ----
        lampada15 = conn.execute("SELECT id FROM familias WHERE nome='Lâmpada'").fetchone()
        lampada14 = conn.execute("SELECT id FROM familias WHERE nome='Lampada'").fetchone()
        lampadas26 = conn.execute("SELECT id FROM familias WHERE nome='Lâmpadas'").fetchone()

        if lampada15 and lampada14:
            conn.execute(
                "UPDATE produtos_cadastro SET familia_id=? WHERE familia_id=?",
                (lampada15[0], lampada14[0]),
            )
        if lampada15 and lampadas26:
            conn.execute(
                "UPDATE produtos_cadastro SET familia_id=? WHERE familia_id=?",
                (lampada15[0], lampadas26[0]),
            )

        # ---- 7. Remover famílias vazias ----
        nomes_remover = [v for k, v in FAMILIAS_REMOVER.items()]
        for nome in nomes_remover:
            conn.execute(
                "DELETE FROM familia_atributos WHERE familia_id=(SELECT id FROM familias WHERE nome=?)",
                (nome,),
            )
            conn.execute("DELETE FROM familias WHERE nome=?", (nome,))

        # ---- 8. Produtos em "Importados" sem variações → familia_id = NULL ----
        for r in conn.execute(
            "SELECT p.id FROM produtos_cadastro p WHERE p.familia_id=? AND p.ativo=1 "
            "AND NOT EXISTS (SELECT 1 FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1)",
            (ID_IMPORTADOS,),
        ).fetchall():
            conn.execute(
                "UPDATE produtos_cadastro SET familia_id=NULL, atualizado_em=datetime('now') WHERE id=?",
                (r[0],),
            )

        # ---- 9. Limpar atributos órfãos antes do FK check ----
        for r in conn.execute("PRAGMA foreign_key_check").fetchall():
            tabela = r[0]
            if tabela == "variante_atributos":
                conn.execute("DELETE FROM variante_atributos WHERE id=?", (r[1],))

        violacoes = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violacoes:
            raise RuntimeError(f"foreign_key_check falhou: {violacoes}")

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def backward(conn: sqlite3.Connection) -> None:
    """Reconstrói schema antigo com familia_id NOT NULL."""
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("BEGIN")
    try:
        conn.execute("""
            CREATE TABLE produtos_cadastro_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                familia_id INTEGER NOT NULL REFERENCES familias(id),
                nome TEXT NOT NULL,
                marca TEXT DEFAULT '',
                descricao TEXT DEFAULT '',
                categoria_id INTEGER REFERENCES categorias(id),
                subcategoria_id INTEGER REFERENCES subcategorias(id),
                termos_busca TEXT DEFAULT '',
                embalagem TEXT DEFAULT '',
                url TEXT DEFAULT '',
                external_id INTEGER,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                atualizado_em TEXT,
                linha_produto TEXT DEFAULT '',
                classe_abc TEXT DEFAULT '',
                ordem_abc INTEGER DEFAULT 0,
                margem_lucro_estimada REAL,
                giro_esperado_mercado REAL,
                valor_agregado TEXT DEFAULT '',
                lucro_total_estimado REAL,
                em_linha INTEGER DEFAULT 1
            )
        """)
        # Produtos com familia_id NULL são descartados (não cabem no schema antigo)
        conn.execute("""
            INSERT INTO produtos_cadastro_old SELECT * FROM produtos_cadastro
            WHERE familia_id IS NOT NULL
        """)
        conn.execute("DROP TABLE produtos_cadastro")
        conn.execute("ALTER TABLE produtos_cadastro_old RENAME TO produtos_cadastro")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos_cadastro(nome COLLATE NOCASE)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_familia ON produtos_cadastro(familia_id)")
        conn.execute("PRAGMA foreign_key_check")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
