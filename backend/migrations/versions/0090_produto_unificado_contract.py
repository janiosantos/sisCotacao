"""Migração 0090 — Unificação produto/variante (Contract, v2.26.0).

Etapa F (Contract) do plano Expand→Migrate→Contract: elimina as tabelas do
modelo de variantes que já não são usadas por código nenhum:

- `variantes` — substituída por `produtos_cadastro` (cada antiga variante é um
  produto; os dados operacionais foram herdados na 0085 e os atributos na 0088).
- `variante_atributos` — EAV dos atributos de variante; os valores foram
  movidos para `produtos_cadastro.atributos` (JSONB) na 0088.
- `variante_produto_map` — tabela de apoio do reapontamento (0086/0087);
  cumpriu seu papel.

Nenhum código (backend, frontend ou testes) referencia mais estas tabelas
(verificado). O rollback desta migração exige restore do backup pré-migração
(backup gerado antes de aplicar); não é reversível via backward().
"""
from __future__ import annotations

VERSION = 90
RISCO = "critica"
NAME = "produto_unificado_contract"

MUDANCA = {
    "o_que": [
        "DROP das tabelas variantes, variante_atributos e variante_produto_map",
        "Elimina a FK variante_atributos.variante_id -> variantes(id)",
    ],
    "porque": [
        "Contract do plano Expand→Migrate→Contract: o modelo unificado usa apenas produtos_cadastro",
        "Nenhum código referencia mais as tabelas de variantes",
        "Dados preservados: operacionais em produtos_cadastro (0085) e atributos em produtos_cadastro.atributos (0088)",
    ],
}


def guard(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables"
        " WHERE table_schema='public' AND table_name='variantes'"
    ).fetchone()
    return row is None


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # variante_atributos primeiro (possui FK -> variantes(id)).
        conn.execute("DROP TABLE IF EXISTS variante_atributos")
        conn.execute("DROP TABLE IF EXISTS variante_produto_map")
        conn.execute("DROP TABLE IF EXISTS variantes")
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    # Destrutiva: o schema original (0052/0053) recria as tabelas num banco
    # vazio, mas os DADOS de variantes só podem ser recuperados via restore do
    # backup pré-migração. Não tenta recriar aqui.
    raise NotImplementedError(
        "Migração destrutiva (Contract 0090): para reverter, restaure o backup "
        "pré-migração — o esquema é recriado pelas migrações 0052/0053."
    )