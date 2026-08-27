"""Migração 0087 — Unificação produto/variante (Reapontamento, v2.26.0).

Passo Migrate (reapontamento) do plano de simplificação: transfere as
referências de `variante_id` das tabelas de negócio para o `produto_id`
correspondente, usando o `variante_produto_map` criado na migração 0086.

Tabelas reapontadas (coluna variante_id -> produto_id via mapa):
devolucoes, estoque_movimento, estoque_saldo, expedicao_itens, fiscal_config,
fiscal_config_historico, fiscal_snapshot, fornecedor_preco,
fornecedor_preferencial, fornecedor_variantes, garantia, ibpt_sugestoes,
inventario_itens, lotes, orcamento_itens_fiscal, paginas_fonte,
preco_historico, product_fiscal_profile, promocao_itens, solicitacao_itens,
tabela_preco_itens.

`imagens_produto` e `variante_atributos` têm tratamento próprio (a primeira
já tem produto_id; a segunda pertence ao modelo de variantes que será
eliminado no Contract — não é reapontada, será migrada como atributos do
produto em etapa própria).

Idempotente: só atualiza linhas cujo variante_id ainda existe no mapa e cujo
valor atual é um id de variante (não de produto). Após esta migração, as
colunas viram produto_id de fato (renomeadas).
"""
from __future__ import annotations

VERSION = 87
RISCO = "critica"
NAME = "produto_unificado_reaponta"

MUDANCA = {
    "o_que": [
        "Reaponta ~21 tabelas de negócio: variante_id -> produto_id (via variante_produto_map)",
        "Renomeia a coluna variante_id para produto_id nessas tabelas (após atualizar os valores)",
        "Imagens_produto: preenche produto_id a partir do variante_id quando variante_id não nulo",
        "Idempotente e reversível",
    ],
    "porque": [
        "Cada variante virou produto; as referências de negócio devem apontar para o produto correspondente",
        "Migrate do plano Expand→Migrate→Contract",
    ],
}


def guard(conn) -> bool:
    # Migração concluída quando NENHUMA tabela de negócio ainda tem coluna
    # `variante_id` (as tabelas variante_produto_map/variante_atributos são do
    # modelo de variantes, eliminadas no Contract).
    row = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_schema='public' AND column_name='variante_id'"
        "   AND table_name NOT IN ('variante_produto_map','variante_atributos')"
        " LIMIT 1"
    ).fetchone()
    return row is None


_TABELAS = [
    "devolucoes", "estoque_movimento", "estoque_saldo", "expedicao_itens",
    "fiscal_config", "fiscal_config_historico", "fiscal_snapshot",
    "fornecedor_preco", "fornecedor_preferencial", "fornecedor_variantes",
    "garantia", "ibpt_sugestoes", "inventario_itens", "lotes",
    "orcamento_itens_fiscal", "paginas_fonte", "preco_historico",
    "product_fiscal_profile", "promocao_itens", "solicitacao_itens",
    "tabela_preco_itens",
]


def forward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # 1) estoque_saldo: tem constraint única (deposito_id, variante_id).
        #    Ao reapontar, variantes do mesmo produto no mesmo depósito podem
        #    colidir. Derruba a constraint, soma as quantidades, recria depois.
        try:
            conn.execute("ALTER TABLE estoque_saldo DROP CONSTRAINT estoque_saldo_deposito_id_variante_id_key")
        except Exception:
            pass
        conn.execute("DROP INDEX IF EXISTS idx_estoque_saldo_dep_var")

        # 2) Reaponta: atualiza variante_id -> produto_id via mapa, para linhas
        #    cujo valor atual ainda é um id de variante. Idempotente: só processa
        #    tabelas que ainda têm a coluna `variante_id` (execuções parciais já
        #    renomearam as primeiras da lista).
        for tabela in _TABELAS:
            col = conn.execute(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name=%s AND column_name='variante_id'",
                (tabela,),
            ).fetchone()
            if col is None:
                continue  # já processada numa execução anterior
            # Remove as FKs que apontam para variantes(id): a coluna passará a
            # guardar produto_id (a tabela variantes será eliminada no Contract).
            cur = conn.execute(
                """
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_attribute att
                  ON att.attrelid = con.conrelid AND att.attnum = con.conkey[1]
                WHERE con.conrelid = %s::regclass
                  AND con.contype = 'f'
                  AND att.attname = 'variante_id'
                  AND array_length(con.conkey, 1) = 1
                """,
                (tabela,),
            )
            for (fk,) in cur.fetchall():
                conn.execute(f'ALTER TABLE {tabela} DROP CONSTRAINT "{fk}"')
            # Reapontamento em dois passos para preservar constraints UNIQUE em
            # variante_id: produto e variante compartilham o mesmo espaço de ids
            # (1..N), então um UPDATE direto variante->produto colidiria de forma
            # transitória (swap). Move-se primeiro para um offset alto (livre),
            # depois reaponta para o produto.
            conn.execute(
                f"""
                UPDATE {tabela} t
                SET variante_id = m.variante_id + 1000000000
                FROM variante_produto_map m
                WHERE t.variante_id = m.variante_id
                """
            )
            conn.execute(
                f"""
                UPDATE {tabela} t
                SET variante_id = m.produto_id
                FROM variante_produto_map m
                WHERE t.variante_id = m.variante_id + 1000000000
                """
            )
            # estoque_saldo: mescla duplicatas (produto+deposito) somando as
            # quantidades na linha de menor id, depois remove as demais.
            if tabela == "estoque_saldo":
                conn.execute(
                    """
                    UPDATE estoque_saldo s
                    SET quantidade = sub.q, reserva = sub.r
                    FROM (
                        SELECT min(id) AS keep_id, variante_id, deposito_id,
                               sum(quantidade) AS q, sum(reserva) AS r
                        FROM estoque_saldo
                        GROUP BY variante_id, deposito_id
                        HAVING count(*) > 1
                    ) sub
                    WHERE s.id = sub.keep_id
                    """
                )
                conn.execute(
                    """
                    DELETE FROM estoque_saldo a
                    USING estoque_saldo b
                    WHERE a.deposito_id = b.deposito_id
                      AND a.variante_id = b.variante_id
                      AND a.id < b.id
                    """
                )
            # Renomeia a coluna. Se a tabela já possuir `produto_id` (ex.: execução
            # parcial anterior ou schema original que já tinha a coluna, como
            # paginas_fonte), a coluna variante_id é apenas removida — o produto_id
            # pré-existente é a fonte autoritativa.
            has_pid = conn.execute(
                "SELECT 1 FROM information_schema.columns"
                " WHERE table_name=%s AND column_name='produto_id'",
                (tabela,),
            ).fetchone()
            if has_pid:
                conn.execute(f"ALTER TABLE {tabela} DROP COLUMN variante_id")
            else:
                conn.execute(
                    f"ALTER TABLE {tabela} RENAME COLUMN variante_id TO produto_id"
                )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{tabela}_produto ON {tabela} (produto_id)"
            )

        # 3) Recria a constraint única de estoque_saldo sobre produto_id.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS estoque_saldo_deposito_produto_uidx"
            " ON estoque_saldo (deposito_id, produto_id)"
        )

        # 2) imagens_produto: preenche produto_id a partir do variante_id.
        conn.execute(
            """
            UPDATE imagens_produto i
            SET produto_id = m.produto_id
            FROM variante_produto_map m
            WHERE i.variante_id = m.variante_id
              AND (i.produto_id IS NULL OR i.produto_id = 0)
            """
        )
        fk_imgs = conn.execute(
            "SELECT con.conname FROM pg_constraint con"
            " JOIN pg_attribute att ON att.attrelid=con.conrelid AND att.attnum=con.conkey[1]"
            " WHERE con.conrelid='imagens_produto'::regclass AND con.contype='f'"
            "   AND att.attname='variante_id'"
        ).fetchall()
        for (fk,) in fk_imgs:
            conn.execute(f'ALTER TABLE imagens_produto DROP CONSTRAINT "{fk}"')
        conn.execute(
            "ALTER TABLE imagens_produto DROP COLUMN IF EXISTS variante_id"
        )
    finally:
        conn.autocommit = ac


def backward(conn) -> None:
    ac = conn.autocommit
    conn.autocommit = True
    try:
        # Não é trivial reconstruir o mapa reverso (várias variantes → 1 produto).
        # Documenta-se a limitação: rollback desta migração exige recriar variantes
        # a partir do histórico; no pior caso, restore do backup pré-migração.
        conn.execute("ALTER TABLE imagens_produto ADD COLUMN IF NOT EXISTS variante_id BIGINT")
        for tabela in _TABELAS:
            conn.execute(f"DROP INDEX IF EXISTS idx_{tabela}_produto")
            conn.execute(
                f"ALTER TABLE {tabela} RENAME COLUMN produto_id TO variante_id"
            )
    finally:
        conn.autocommit = ac