"""Curva ABC do catálogo (classificação preventiva de margem de contribuição).

Como o negócio está iniciando (sem histórico de vendas), o catálogo é
classificado pelo **Potencial de Margem de Contribuição Total Estimado**:

    lucro_unitario_estimado = preco_venda * margem_lucro_estimada
    lucro_total_estimado    = lucro_unitario_estimado * giro_esperado_mercado

Os parâmetros de mercado (`margem_lucro_estimada`, `giro_esperado_mercado`,
`valor_agregado`) são inferidos da **linha de produto** (muito derivada da
categoria do breadcrumb da loja) usando a tabela `LINHA_PARAMETROS`.

Depois ordena-se todos os produtos por `lucro_total_estimado` decrescente e
aplica-se o corte acumulado:
    Classe A → até 70% do resultado estimado acumulado
    Classe B → de 70% a 90%
    Classe C → os 10% restantes (mix de reposição)

A classe A é a prioridade para a RFQ (cotação agressiva por preço, maior
impacto financeiro).
"""
from __future__ import annotations

import sqlite3
from typing import Any

from catalog_server.db import system_conn

# ---------------------------------------------------------------------------
# Tabela de parâmetros iniciais por linha de produto.
#   margem = fração estimada de margem de contribuição unitária (0..1)
#   giro   = fator de giro esperado de mercado (0..1, "percentual" estimado)
#   valor  = valor agregado (texto para consulta/rastreabilidade)
#   classe = classe ABC sugerida pela análise de negócio (baseline p/ revisão)
# ---------------------------------------------------------------------------
LINHA_PARAMETROS: dict[str, dict[str, Any]] = {
    "Fios e Cabos": {"giro": 0.95, "margem": 0.175, "valor": "Alto", "classe": "A"},
    "Tubos PVC": {"giro": 0.80, "margem": 0.225, "valor": "Medio/Alto", "classe": "A"},
    "Maquinas Eletricas": {"giro": 0.55, "margem": 0.375, "valor": "Muito Alto", "classe": "A"},
    "Tomadas e Interruptores": {"giro": 0.65, "margem": 0.45, "valor": "Baixo/Medio", "classe": "B"},
    "Material Eletrico (Diversos)": {"giro": 0.65, "margem": 0.45, "valor": "Baixo/Medio", "classe": "B"},
    "Conexoes PVC": {"giro": 0.80, "margem": 0.50, "valor": "Baixo", "classe": "B"},
    "Ferramentas Manuais": {"giro": 0.40, "margem": 0.40, "valor": "Medio", "classe": "B"},
    "Instrumentos de Medicao": {"giro": 0.40, "margem": 0.45, "valor": "Medio/Alto", "classe": "B"},
    "Hidraulica (Registros e Torneiras)": {"giro": 0.60, "margem": 0.40, "valor": "Medio/Alto", "classe": "B"},
    "Iluminacao": {"giro": 0.60, "margem": 0.45, "valor": "Medio", "classe": "B"},
    "Solda": {"giro": 0.40, "margem": 0.45, "valor": "Medio", "classe": "B"},
    "Movimentacao de Carga": {"giro": 0.40, "margem": 0.40, "valor": "Medio/Alto", "classe": "B"},
    "Organizacao e Armazenagem": {"giro": 0.50, "margem": 0.40, "valor": "Medio", "classe": "B"},
    "Automotivo": {"giro": 0.50, "margem": 0.45, "valor": "Medio", "classe": "B"},
    "Construcao Civil": {"giro": 0.70, "margem": 0.35, "valor": "Medio", "classe": "B"},
    "Casa e Jardim": {"giro": 0.55, "margem": 0.40, "valor": "Medio", "classe": "B"},
    "Seguranca e Alarme": {"giro": 0.50, "margem": 0.45, "valor": "Medio/Alto", "classe": "B"},
    "Fitas e Vedacao": {"giro": 0.80, "margem": 0.55, "valor": "Muito Baixo", "classe": "C"},
    "Colas Adesivos e Lubrificantes": {"giro": 0.60, "margem": 0.55, "valor": "Baixo", "classe": "C"},
    "Abrasivos": {"giro": 0.80, "margem": 0.55, "valor": "Muito Baixo", "classe": "C"},
    "EPI": {"giro": 0.70, "margem": 0.50, "valor": "Baixo", "classe": "C"},
    "Parafusos e Miudezas": {"giro": 0.55, "margem": 0.55, "valor": "Ultra Baixo", "classe": "C"},
    "Limpeza": {"giro": 0.60, "margem": 0.45, "valor": "Baixo", "classe": "C"},
    "Geral": {"giro": 0.50, "margem": 0.35, "valor": "Medio", "classe": "B"},
}

# Cortes da Curva ABC (frações acumuladas do resultado estimado).
CLASSE_A_LIMITE = 0.70
CLASSE_B_LIMITE = 0.90

# -------- Escopo inicial da loja (Rolar) ----------------------------------
# O negócio inicia focando ferramentas manuais / elétricas de baixo custo,
# material elétrico, hidráulica e parafusos. Equipamentos de alto valor
# (máquinas) ficam FORA do rolar inicial por limiar de preço e/ou keyword.
PRECO_LIMITE_EM_LINHA = 3000.0

# Palavras-chave de equipamentos/máquinas (mesmo abaixo do limiar de preço).
_EQUIP_KEYWORDS = (
    "empilhadeira", "retratil", "contrabalancada", "transpaleteira",
    "termofusora", "topo fusao", "guincho", "talha eletrica", "grua",
    "escavadeira", "retroescavadeira", "trator", "gerador", "grupo gerador",
    "plataforma elevatoria", "compressor de ar parafuso", "caldeira",
    "serra de mesa profissional", "quebra gelo", "roçadeira tratorizada",
    "maquina de solda inversora industrial",
)


def fora_de_linha(preco_max: float | None = None, categoria: str = "", nome: str = "") -> bool:
    """Decide se o produto fica fora do rolar inicial (equip. alto valor)."""
    if preco_max is not None and preco_max >= PRECO_LIMITE_EM_LINHA:
        return True
    alvo = _norm(f"{categoria} {nome}")
    return any(k in alvo for k in _EQUIP_KEYWORDS)


def marcar_em_linha(dry: bool = False) -> dict:
    """Marca `em_linha` (1=no rolar) para cada produto, por preço/keyword.

    Idempotente: recomputa dos dados (preço máximo da variante + nome/categoria).
    Devolve contagem de fora de linha.
    """
    with system_conn() as conn:
        rows = conn.execute(
            """SELECT p.id, cat.nome AS categoria, sub.nome AS subcategoria, p.nome,
                      (SELECT MAX(v.preco) FROM variantes v
                       WHERE v.produto_id=p.id AND v.ativo=1) AS preco_max
               FROM produtos_cadastro p
               LEFT JOIN categorias cat ON cat.id=p.categoria_id
               LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"""
        ).fetchall()
    fora = dentro = 0
    updates: list[tuple[int, int]] = []
    for r in rows:
        caminho = _join_path(r["categoria"], r["subcategoria"])
        em = 0 if fora_de_linha(r["preco_max"], caminho, r["nome"]) else 1
        if em == 0:
            fora += 1
        else:
            dentro += 1
        if not dry:
            updates.append((em, r["id"]))
    if not dry:
        with system_conn() as conn:
            conn.executemany(
                "UPDATE produtos_cadastro SET em_linha=? WHERE id=?", updates
            )
    return {"fora_de_linha": fora, "em_linha": dentro, "total": len(updates)}


def _norm(text: str) -> str:
    import unicodedata

    return (
        unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower().strip()
    )


def _join_path(categoria: str = "", subcategoria: str = "") -> str:
    """Junta raiz + folha no caminho de exibição (preserva a folha p/ ABC)."""
    return " > ".join(s for s in (categoria, subcategoria) if (s or "").strip())


def linha_de_categoria(categoria: str = "", nome: str = "") -> str:
    """Inferência inicial da linha de produto a partir da categoria/descrição.

    Regras por palavras-chave no caminho de categoria do breadcrumb + nome. A
    primeira regra que casar vence; senão usa a linha "Geral". Ordenadas da
    mais específica para a mais genérica.
    """
    nc = _norm(categoria or "")
    nn = _norm(nome or "")
    alvo = f"{nc} {nn}".strip()

    # 1) Despacho determinístico pela taxonomia do site (categoria do breadcrumb).
    for chave, linha in (
        ("movimentacao de carga", "Movimentacao de Carga"),
        ("organizacao e armazenagem", "Organizacao e Armazenagem"),
        ("equipamento auto center", "Automotivo"),
        ("construcao civil", "Construcao Civil"),
        ("material eletrico", "Material Eletrico (Diversos)"),
        ("iluminacao", "Iluminacao"),
        ("hidraulica", "Hidraulica (Registros e Torneiras)"),
        ("parafuso", "Parafusos e Miudezas"),
        ("acessorios para ferramentas", "Ferramentas Manuais"),
        ("ferramentas manuais", "Ferramentas Manuais"),
        ("maquinas ferramentas", "Maquinas Eletricas"),
        ("ferramentas eletricas", "Maquinas Eletricas"),
        ("instrumentos", "Instrumentos de Medicao"),
        ("fios e cabos", "Fios e Cabos"),
        ("limpeza", "Limpeza"),
        ("ventiladores", "Casa e Jardim"),
        ("ventilador", "Casa e Jardim"),
        ("exaustor", "Casa e Jardim"),
        ("jardinagem", "Casa e Jardim"),
        ("compressores de ar", "Maquinas Eletricas"),
        ("compressor", "Maquinas Eletricas"),
        ("funilaria", "Automotivo"),
        ("fixacao", "Parafusos e Miudezas"),
        ("movimentacao e carga", "Movimentacao de Carga"),
        ("movimentacao", "Movimentacao de Carga"),
    ):
        if chave in nc:
            return linha

    regras: list[tuple[tuple[str, ...], str]] = [
        (("fios e cabos", "cabo flex", "cabo ", "hepr", "fiacao", "fio "), "Fios e Cabos"),
        (("tubo pvc", "tubo ", "esgoto", "saneamento", "agua fria", "agua quente", "caixa dagua", "canaliz"), "Tubos PVC"),
        (("chumbador", "parabolt", "barra roscada", "porca", "arruela", "prego", "parafuso", "fixador", "cavilha", "pino", "rebite", "bucha"), "Parafusos e Miudezas"),
        (("fita isolante", "fita veda", "veda rosca", "fita crepe", "fita dupla", "fita laca", "silicone", "anel de vedacao", "reparo de registro", "borracha"), "Fitas e Vedacao"),
        (("lampada", "luminar", "refletor", "led", "bulbo", "bocal", "spothood", "spot led", "fita led"), "Iluminacao"),
        (("solda", "soldagem", "mascarico", "eletrodo", "inversora de solda", "tocha", "arame de solda", "fluxo solda"), "Solda"),
        (("disco de corte", "disco de desbaste", "abrasiv", "lixa", "rebolo", "polimento", "escova rotativa", "flap"), "Abrasivos"),
        (("cola", "adesivo", "lubrificante", "graxa", "oleo", "desengripante", "spray de silicone", "silicone spray"), "Colas Adesivos e Lubrificantes"),
        (("alarme", "camera", "cameras", "sirene", "preventivo", "detector", "acionador", "incendio", "balun", "extintor", "vigilancia", "sensor de presenca", "sensor de fuma"), "Seguranca e Alarme"),
        (("capacete", "luva", "oculos", "botina", "protetor auricular", "mascara", "respirador", "cinto de seguranca", "epi"), "EPI"),
        (("empilhadeira", "transpaleteira", "guincho", "talha", "cinta", "eslinga", "corda", "roldana", "palete", "carrinho de carga", "elevacao de carga", "estrado", "gancho de carga"), "Movimentacao de Carga"),
        (("caixa organizadora", "organizacao", "estante", "prateleira", "gaveteiro", "armario", "bancada", "carrinho de armazenamento"), "Organizacao e Armazenagem"),
        (("lubrificante automotivo", "oleo motor", "automotivo", "pistola de pintura", "pneu", "bateria automotiva"), "Automotivo"),
        (("construcao", "cimento", "argamassa", "massa corrida", "massa acrilica", "tinta", "pincel", "rolo de pintura", "trincha", "impermeabil", "rejunte", "gesso", "drywall", "tijolo", "pedra", "revestimento", "lona", "lona", "vergalhao", "corta vergalhao", "marcador", "porcelanato", "piso", "cuba", "gerador", "motor a gasolina", "motor a diesel"), "Construcao Civil"),
        (("casa e jardim", "jardim", "lanterna", "pulverizador", "regador", "vassoura", "escada", "vaso", "carrinho de mao"), "Casa e Jardim"),
        (("terminal", "barramento", "condulete", "contator", "dps", "protetor surto", "caixa de luz", "caixa eletrica", "abraçadeira", "bornes", "borne", "fusivel", "eletroduto", "canaleta", "quadro de distribuicao", "plugue", "modulo", "placa", "partida", "botao", "motor"), "Material Eletrico (Diversos)"),
        (("tomada", "interruptor", "disjuntor", "espelho", "rele", "relé", "botao", "pluga", "conector", "soquete eletrico"), "Tomadas e Interruptores"),
        (("medicao", "medidor", "instrumento", "multimetro", "paquimetro", "micrometro", "nivel a laser", "trena", "detector de tensao", "manometro", "termometro", "esquadro"), "Instrumentos de Medicao"),
        (("ferramenta eletrica", "maquina", "furadeira", "parafusadeira", "esmerilhadeira", "serra ", "martelete", "soprador", "retifica", "tupia", "lixadeira", "politriz", "cortador", "roçadeira", "rosadeira", "motoesmeril", "a bateria", "ferramentas pneum"), "Maquinas Eletricas"),
        (("registro", "torneira", "hidraul", "chuveiro", "ducha", "ralo", "grelha", "sifao", "engate", "tornei", "vazamento", "cilindro", "valvula", "mangote", "conexao hidraul"), "Hidraulica (Registros e Torneiras)"),
        (("ferramenta", "alicate", "chave ", "martelo", "soquete", "broca", "formao", "cinzel", "lima", "serrote", "estilete", "facao", "talhadeira", "garras", "torquimetro", "saca", "extrator", "acessorio para ferramenta"), "Ferramentas Manuais"),
    ]
    for chaves, linha in regras:
        if any(chave in alvo for chave in chaves):
            return linha
    return "Geral"


def _parametros(linha: str) -> dict[str, Any]:
    return LINHA_PARAMETROS.get(linha, LINHA_PARAMETROS["Geral"])


# ---------------------------------------------------------------------------

def preencher_parametros(dry: bool = False) -> tuple[int, int]:
    """Preenche linha_produto/margem/giro/valor_agregado para produtos sem valor.

    A margem e o giro são estimativas de mercado aplicadas por linha; um
    produto que já tenha valor preenchido manualmente não é sobrescrito.
    Devolve (produtos atualizados, produtos sem linha identificada).
    """
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT p.id, cat.nome AS categoria, sub.nome AS subcategoria, p.nome"
            " FROM produtos_cadastro p"
            " LEFT JOIN categorias cat ON cat.id=p.categoria_id"
            " LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id"
            " WHERE (p.linha_produto IS NULL OR p.linha_produto='' OR p.linha_produto='Geral')"
        ).fetchall()
    atualizados = 0
    sem_linha = 0
    with system_conn() as conn:
        for r in rows:
            caminho = _join_path(r["categoria"], r["subcategoria"])
            linha = linha_de_categoria(caminho, r["nome"])
            p = _parametros(linha)
            if linha == "Geral":
                sem_linha += 1
            if not dry:
                conn.execute(
                    "UPDATE produtos_cadastro SET linha_produto=?, margem_lucro_estimada=?,"
                    " giro_esperado_mercado=?, valor_agregado=? WHERE id=?",
                    (linha, p["margem"], p["giro"], p["valor"], r["id"]),
                )
            atualizados += 1
    return atualizados, sem_linha


# ---------------------------------------------------------------------------

_BOOTSTRAP_SQL = """
WITH base AS (
    SELECT p.id,
           COALESCE(p.giro_esperado_mercado, 0.0)   AS giro,
           COALESCE(p.margem_lucro_estimada, 0.0)   AS margem,
           COALESCE((
               SELECT AVG(v.preco) FROM variantes v
               WHERE v.produto_id = p.id AND v.ativo = 1
           ), COALESCE((
               SELECT AVG(v.preco_venda) FROM variantes v
               WHERE v.produto_id = p.id AND v.ativo = 1
           ), 0.0))                                  AS preco_venda,
           COALESCE((
               SELECT AVG(v.custo_unitario) FROM variantes v
               WHERE v.produto_id = p.id AND v.ativo = 1 AND v.custo_unitario IS NOT NULL
           ), 0.0)                                  AS custo_unitario
    FROM produtos_cadastro p
    WHERE p.em_linha = 1
),
com_lucro AS (
    SELECT b.id,
           b.preco_venda,
           b.custo_unitario,
           CASE
               WHEN b.custo_unitario > 0 AND b.preco_venda > 0
                    THEN b.preco_venda - b.custo_unitario              -- custo real informado
               ELSE b.preco_venda * b.margem                          -- margem estimada preventiva
           END                                     AS lucro_unitario,
           b.giro
    FROM base b
),
total AS (
    SELECT c.id,
           c.preco_venda,
           c.custo_unitario,
           c.lucro_unitario,
           (c.lucro_unitario * c.giro)             AS lucro_total_estimado
    FROM com_lucro c
),
acum AS (
    SELECT t.id,
           t.lucro_total_estimado,
           SUM(t.lucro_total_estimado) OVER (ORDER BY t.lucro_total_estimado DESC, t.id) AS acumulado,
           SUM(t.lucro_total_estimado) OVER ()     AS total_geral,
           ROW_NUMBER() OVER (ORDER BY t.lucro_total_estimado DESC, t.id) AS ordem
    FROM total t
)
SELECT a.id, a.lucro_total_estimado, a.acumulado, a.total_geral, a.ordem,
       CASE
           WHEN a.total_geral <= 0 THEN NULL
           ELSE 1.0 * a.acumulado / a.total_geral
       END AS pct_acumulado
FROM acum a
"""


def _classe_para_pct(pct: float | None) -> str:
    if pct is None or pct <= CLASSE_A_LIMITE:
        return "A"
    if pct <= CLASSE_B_LIMITE:
        return "B"
    return "C"


def calcular_curva() -> list[dict]:
    """Calcula a curva ABC completa (sem gravar). Devolve linhas ordenadas."""
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(_BOOTSTRAP_SQL).fetchall()]


def aplicar_curva(dry: bool = False) -> dict:
    """Aplica a Curva ABC: classe_abc + ordem_abc + lucro_total_estimado.

    Produtos sem lucro estimado (preço/parâmetros ausentes) recebem classe 'C'
    (mix de baixa prioridade) e ficam no fim da ordem.
    """
    linhas = calcular_curva()
    if not linhas:
        return {"atualizados": 0, "resumo": {}, "total_geral": 0.0}

    total_geral = max(linhas[0]["total_geral"] or 0.0, 1e-12)
    n = len(linhas)
    sem_preco = 0
    classe_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    classe_soma: dict[str, float] = {"A": 0.0, "B": 0.0, "C": 0.0}

    updates: list[tuple[str, int, float, int]] = []
    for i, r in enumerate(linhas, start=1):
        lt = r["lucro_total_estimado"] or 0.0
        if lt <= 0:
            classe = "C"
            ordem = n - sem_preco if False else i
            sem_preco += 1
        else:
            classe = _classe_para_pct(r["pct_acumulado"])
            ordem = r["ordem"]
        classe_counts[classe] += 1
        classe_soma[classe] += lt
        if not dry:
            updates.append((classe, ordem, round(lt, 4), r["id"]))

    if not dry:
        with system_conn() as conn:
            conn.executemany(
                "UPDATE produtos_cadastro SET classe_abc=?, ordem_abc=?,"
                " lucro_total_estimado=? WHERE id=?",
                updates,
            )

    return {
        "atualizados": len(updates),
        "total_geral": round(total_geral, 2),
        "sem_lucro": sem_preco,
        "resumo": {
            "A": {"produtos": classe_counts["A"], "resultado": round(classe_soma["A"] / total_geral * 100, 1)},
            "B": {"produtos": classe_counts["B"], "resultado": round(classe_soma["B"] / total_geral * 100, 1)},
            "C": {"produtos": classe_counts["C"], "resultado": round(classe_soma["C"] / total_geral * 100, 1)},
        },
    }


# ---------------------------------------------------------------------------
# Logística de cotação (RFQ): priorizar a Classe A.
# ---------------------------------------------------------------------------

def prioridade_cotacao(
    classes: tuple[str, ...] = ("A",),
    linhas: tuple[str, ...] = (),
    limit: int = 0,
) -> list[dict]:
    """Itens para a RFQ, priorizados por ordem_abc (maior impacto financeiro).

    `classes` = classes incluídas (default Classe A); `linhas` = filtro opcional
    de linha de produto; `limit` = 0 retorna todos.
    """
    if not classes:
        return []
    placeholders = ",".join("?" * len(classes))
    where = [f"p.classe_abc IN ({placeholders})"]
    params: list = list(classes)
    if linhas:
        ph2 = ",".join("?" * len(linhas))
        where.append(f"p.linha_produto IN ({ph2})")
        params += list(linhas)
    where.append("p.ativo=1")
    where.append("p.em_linha=1")
    where.append("EXISTS (SELECT 1 FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1)")
    sql = f"""
        SELECT p.id, p.nome, p.marca, p.linha_produto,
               cat.nome AS categoria, sub.nome AS subcategoria,
               p.classe_abc, p.ordem_abc, p.margem_lucro_estimada,
               p.giro_esperado_mercado, p.lucro_total_estimado,
               (SELECT MIN(v.preco) FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1) AS preco_min,
               (SELECT MIN(v.custo_unitario) FROM variantes v WHERE v.produto_id=p.id AND v.ativo=1 AND v.custo_unitario IS NOT NULL) AS custo_medio
        FROM produtos_cadastro p
        LEFT JOIN categorias cat ON cat.id=p.categoria_id
        LEFT JOIN subcategorias sub ON sub.id=p.subcategoria_id
        WHERE {' AND '.join(where)}
        ORDER BY p.ordem_abc ASC
    """
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def resumo_curva() -> dict:
    """Distribuição atual da curva ABC por classe e por linha."""
    with system_conn() as conn:
        por_classe = [
            dict(r)
            for r in conn.execute(
                "SELECT classe_abc AS classe, COUNT(*) AS produtos,"
                " ROUND(SUM(lucro_total_estimado),2) AS resultado"
                " FROM produtos_cadastro WHERE classe_abc <> '' GROUP BY classe_abc"
                " ORDER BY classe_abc"
            ).fetchall()
        ]
        por_linha = [
            dict(r)
            for r in conn.execute(
                "SELECT linha_produto AS linha, COUNT(*) AS produtos,"
                " COUNT(CASE WHEN classe_abc='A' THEN 1 END) AS classe_a,"
                " COUNT(CASE WHEN classe_abc='C' THEN 1 END) AS classe_c"
                " FROM produtos_cadastro WHERE linha_produto <> '' GROUP BY linha_produto"
                " ORDER BY produtos DESC"
            ).fetchall()
        ]
    return {"por_classe": por_classe, "por_linha": por_linha}