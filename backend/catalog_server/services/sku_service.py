"""Serviço de SKU — geração, normalização, validação e deduplicação.

Centraliza as regras de SKU que hoje estão espalhadas nos fluxos de cadastro:

- `normalizar` — limpa/upperiza o SKU informado;
- `validar` — regras de formato e comprimento (com mensagens amigáveis);
- `gerar` — gera um SKU único para variantes vazias (fallback determinístico);
- `reservar` — garante um SKU único no banco: normaliza, valida, verifica
  duplicidade e (se permitido) aplica sufixo `-N` em conflitos.

Com o índice único parcial criado pela migração 0053 (`idx_variantes_sku_unique`),
o banco passa a impedir SKUs repetidos; o serviço existe para gerar valores
válidos ANTES de tentar gravar e para dar feedback claro ao usuário.
"""
from __future__ import annotations

import re

from catalog_server.db import system_conn

SKU_MAX_LEN = 64
_SKU_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def normalizar(sku: str | None) -> str:
    """Normaliza um SKU: remove espaços, upperiza e compacta repetidos."""
    if not sku:
        return ""
    return re.sub(r"\s+", " ", sku.strip().upper())


def validar(sku: str | None) -> tuple[bool, str]:
    """Valida o SKU. Devolve (ok, motivo_erro). SKU vazio é inválido."""
    sku = normalizar(sku)
    if not sku:
        return False, "SKU não pode ser vazio"
    if len(sku) > SKU_MAX_LEN:
        return False, f"SKU deve ter no máximo {SKU_MAX_LEN} caracteres"
    if not _SKU_RE.match(sku):
        return False, "SKU deve conter apenas letras, números e . _ - /"
    return True, ""


def _ocupado(conn, sku: str, ignorar_id: int | None = None) -> bool:
    if not sku:
        return False
    if ignorar_id is None:
        row = conn.execute(
            "SELECT 1 FROM produtos_cadastro WHERE sku = ?", (sku,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM produtos_cadastro WHERE sku = ? AND id <> ?",
            (sku, ignorar_id),
        ).fetchone()
    return row is not None


def gerar(produto_id: int, base: str | None = None) -> str:
    """Gera um SKU determinístico e único: `base-produto_id-produto_id`.

    `base` pode ser um nome/atributo (ex.: "ILU") para humanizar o SKU.
    """
    prefixo = normalizar(base or "")
    prefixo = prefixo.replace(" ", "-")[:24]
    if prefixo:
        return f"{prefixo}-{produto_id}-{produto_id}"
    return f"SKU-{produto_id}-{produto_id}"


def reservar(
    sku: str | None,
    produto_id: int,
    base: str | None = None,
    ignorar_id: int | None = None,
    resolver_conflito: bool = True,
    conn=None,
) -> tuple[str, str]:
    """Garante um SKU único e válido.

    Devolve (sku_final, aviso). `aviso` não-vazio indica que o SKU foi
    corrigido/gerado automaticamente. Se `resolver_conflito` for False e houver
    duplicidade, devolve um aviso indicando que o valor foi rejeitado (e o
    chamador decide o que fazer).
    """
    conn = conn or system_conn()
    sku = normalizar(sku)

    # Vazio → gera.
    if not sku:
        gerado = gerar(produto_id, base)
        while _ocupado(conn, gerado, ignorar_id):
            gerado += "-X"
        return gerado, "SKU vazio; gerado automaticamente"

    ok, motivo = validar(sku)
    if not ok:
        return "", motivo

    if not _ocupado(conn, sku, ignorar_id):
        return sku, ""

    if not resolver_conflito:
        return "", f"SKU já existe: {sku}"

    # Conflito → sufixa até achar um livre.
    candidato, n = sku, 2
    while _ocupado(conn, candidato, ignorar_id):
        candidato = f"{sku}-{n}"
        n += 1
    return candidato, f"SKU duplicado; ajustado para {candidato}"


def gerar_lote(
    base: str | None,
    itens: list[dict],
    produto_id: int = 0,
    conn=None,
    grupo_cod: str | None = None,
    subgrupo_cod: str | None = None,
    marca_cod: str | None = None,
) -> list[dict]:
    """Gera/valida os SKUs de um lote de variações (interface de cadastro).

    Dois modos:

    **Estruturado** (quando `grupo_cod`/`subgrupo_cod`/`marca_cod` informados):
    compõe ``[GRUPO]-[SUBGRUPO]-[MARCA]-[ATRIBUTOS]``. Cada item traz
    `attrs` (segmento de atributos já slugificado). SKU emitido (venda,
    compra, estoque, NF, integração, histórico) é **mantido inalterado**.

    **Legado** (sem códigos): comportamento anterior — `base` + `sku` por
    item, gerando `{BASE}-{produto_id}-{n}` quando vazio.

    Em ambos, duplicados no lote/banco são sufixados com `-N`.
    """
    if conn is None:
        with system_conn() as conn:
            return _gerar_lote(
                conn, base, itens, produto_id, grupo_cod, subgrupo_cod, marca_cod
            )
    return _gerar_lote(
        conn, base, itens, produto_id, grupo_cod, subgrupo_cod, marca_cod
    )


def _partes_estruturadas(
    grupo_cod: str | None, subgrupo_cod: str | None, marca_cod: str | None
) -> list[str]:
    partes = [
        normalizar(grupo_cod),
        normalizar(subgrupo_cod),
        normalizar(marca_cod),
    ]
    return [p for p in partes if p]


def _gerar_lote(
    conn,
    base: str | None,
    itens: list[dict],
    produto_id: int,
    grupo_cod: str | None,
    subgrupo_cod: str | None,
    marca_cod: str | None,
) -> list[dict]:
    estruturado = any(
        normalizar(c) for c in (grupo_cod, subgrupo_cod, marca_cod)
    )
    prefixo_estrut = "-".join(_partes_estruturadas(grupo_cod, subgrupo_cod, marca_cod))
    prefixo = (normalizar(base or "").replace(" ", "-")[:24] or "SKU")
    usados: set[str] = set()
    out: list[dict] = []
    for i, item in enumerate(itens or [], start=1):
        ignorar_id = item.get("id") or None

        # Imutabilidade: SKU já emitido em operação comercial não é alterado.
        if ignorar_id and sku_emitido(conn, ignorar_id):
            row = conn.execute(
                "SELECT sku FROM produtos_cadastro WHERE id=?", (ignorar_id,)
            ).fetchone()
            sku_atual = normalizar(row["sku"]) if row else ""
            if sku_atual:
                aviso = "SKU emitido (venda/compra/estoque/NF/integração): mantido inalterado"
                out.append({"sku": sku_atual, "aviso": aviso, "emitido": True})
                continue

        if estruturado:
            attrs = normalizar(item.get("attrs") or "")
            sku = "-".join([p for p in (prefixo_estrut, attrs) if p])
            if not sku:
                sku = f"SKU-{produto_id}-{i}" if produto_id else f"SKU-{i}"
            aviso = "SKU estruturado gerado" if not item.get("attrs") else ""
        else:
            sku_in = normalizar(item.get("sku") or "")
            if not sku_in:
                sku = f"{prefixo}-{produto_id}-{i}" if produto_id else f"{prefixo}-{i}"
                aviso = "SKU gerado automaticamente"
            else:
                ok, motivo = validar(sku_in)
                if not ok:
                    out.append({"sku": "", "aviso": motivo})
                    continue
                sku, aviso = sku_in, ""

        n = 2
        while _ocupado(conn, sku, ignorar_id) or sku in usados:
            sku = f"{sku}-{n}"
            n += 1
            if not aviso:
                aviso = f"SKU duplicado; ajustado para {sku}"
        usados.add(sku)
        out.append({"sku": sku, "aviso": aviso})
    return out


# ---------------------------------------------------------------------------
# Imutabilidade do SKU
# ---------------------------------------------------------------------------


def _tabelas_com_produto_id(conn) -> list[str]:
    """Tabelas operacionais que referenciam `produto_id` (uso do SKU)."""
    rows = conn.execute(
        "SELECT table_name FROM information_schema.columns"
        " WHERE column_name='produto_id' AND table_schema='public'"
        "   AND table_name NOT IN ('variante_produto_map','variante_atributos')"
    ).fetchall()
    return [r["table_name"] for r in rows]


def sku_emitido(conn, produto_id: int) -> bool:
    """True se o produto já foi usado em operação comercial (SKU imutável).

    Verifica todas as tabelas que possuem `produto_id` (antiga `produto_id`):
    venda (orcamentos), compra (solicitacoes), estoque (saldo/movimento/lotes),
    nota fiscal (fiscal_config/orcamento_itens_fiscal), integrações
    (fornecedor_*), histórico (preco_historico) etc. Tabelas ausentes no
    ambiente são ignoradas.
    """
    if not produto_id:
        return False
    for t in _tabelas_com_produto_id(conn):
        try:
            row = conn.execute(
                f"SELECT 1 FROM {t} WHERE produto_id=?", (produto_id,)
            ).fetchone()
        except Exception:
            continue
        if row:
            return True
    return False