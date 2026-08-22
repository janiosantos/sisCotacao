"""Migração 0054 — Seeds fiscais de referência.

As tabelas de referência fiscal (`cfop`, `cst_icms`, `cst_pis`, `cst_cofins`,
`csosn`, `beneficios_fiscais`) são criadas vazias pelo baseline 0052; os dados
de catálogo vinham das migrações SQLite legadas (0016 e 0037). Esta migração
replica os mesmos seeds de forma idempotente (`ON CONFLICT DO NOTHING`).

Idempotente: reaplicável a qualquer momento sem duplicar registros.
"""
from __future__ import annotations

VERSION = 54
RISCO = "rotina"

# Documentação da mudança de banco (exigida pelo runner desde a v1.6.2).
MUDANCA = {
    "o_que": ["Popula tabelas de referência fiscal (CFOP/CST/CSOSN etc.)"],
    "porque": ["Base dos módulos fiscal e de precificação"],
}
NAME = "seed_fiscal_referencia"

SEED_CFOP = [
    ("1.102", "Compra para industrialização", "entrada"),
    ("1.111", "Compra para revenda", "entrada"),
    ("1.204", "Compra para revenda (outra UF)", "outra_uf"),
    ("5.102", "Venda de mercadoria adquirida", "saida"),
    ("5.109", "Venda de mercadoria adquirida (NF-e)", "saida"),
    ("6.102", "Venda de mercadoria adquirida (outra UF)", "outra_uf"),
    ("5.405", "Venda de mercadoria (consumidor final)", "saida"),
    ("6.405", "Venda de mercadoria (consumidor final, outra UF)", "outra_uf"),
    ("5.101", "Venda de produção do estabelecimento", "saida"),
    ("2.102", "Devolução de compra para revenda", "entrada"),
    ("2.202", "Devolução de compra para industrialização", "entrada"),
    ("5.201", "Devolução de venda", "saida"),
    ("1.949", "Outra entrada de mercadoria", "entrada"),
    ("5.949", "Outra saída de mercadoria", "saida"),
]

SEED_CST_ICMS = [
    ("00", "Tributada integralmente"),
    ("10", "Tributada com cobrança de ICMS por ST"),
    ("20", "Base de cálculo reduzida"),
    ("30", "Isenta ou não tributada (ST anula ICMS)"),
    ("40", "Isenta"),
    ("41", "Não tributada"),
    ("50", "Suspensão"),
    ("51", "Diferimento"),
    ("60", "ICMS cobrado anteriormente por ST"),
    ("70", "Redução de base + ST"),
    ("90", "Outras"),
]

SEED_CST_PIS = [
    ("01", "Operação Tributável - Alíquota Básica"),
    ("02", "Operação Tributável - Alíquota Diferenciada"),
    ("03", "Operação Tributável - Alíquota por Unidade"),
    ("04", "Operação Tributável - Alíquota Zero"),
    ("05", "Operação Tributável - ST (Substituição Tributária)"),
    ("06", "Operação Tributável - Alíquota Zero (ST)"),
    ("07", "Operação Isenta da Contribuição"),
    ("08", "Operação sem Incidência da Contribuição"),
    ("09", "Operação com Suspensão da Contribuição"),
    ("49", "Outras Operações de Saída"),
    ("50", "Operação com Direito a Crédito"),
    ("51", "Operação sem Direito a Crédito"),
    ("52", "Operação com Crédito Presumido"),
    ("53", "Operação com Alíquota por Unidade"),
    ("54", "Operação com Alíquota por Unidade (Direito a Crédito)"),
    ("55", "Operação com Alíquota por Unidade (sem Direito a Crédito)"),
    ("98", "Outras"),
    ("99", "Outras Operações"),
]

SEED_CSOSN = [
    ("101", "Tributada pelo Simples Nacional com permissão de crédito"),
    ("102", "Tributada pelo Simples Nacional sem permissão de crédito"),
    ("103", "Isenção do ICMS no Simples Nacional para faixa de receita bruta"),
    ("106", "Tributada pelo Simples Nacional com cobrança do ICMS por ST"),
    ("107", "Tributada pelo Simples Nacional com permissão de crédito e ICMS por ST"),
    ("201", "Tributada pelo Simples Nacional com permissão de crédito e ICMS por ST"),
    ("202", "Tributada pelo Simples Nacional sem permissão de crédito e ICMS por ST"),
    ("203", "Isenção do ICMS no Simples Nacional para faixa de receita bruta e ICMS por ST"),
    ("300", "Imune"),
    ("400", "Não tributada pelo Simples Nacional"),
    ("500", "ICMS cobrado anteriormente por ST ou por antecipação"),
    ("900", "Outros"),
]

SEED_BENEFICIOS = [
    ("ISENCAO", "Isenção de ICMS", "isencao", 0),
    ("RED_BASE", "Redução de base de cálculo ICMS", "reducao_base", 20),
    ("CRED_PRES", "Crédito presumido de ICMS", "credito_presumido", 0),
    ("DIFERIDO", "Diferimento do ICMS", "diferimento", 0),
    ("SUSPENSO", "Suspensão do ICMS", "suspensao", 0),
]


def guard(conn) -> bool:
    """Já aplicada se houver dados em `cfop` (última tabela semeada)."""
    try:
        row = conn.execute("SELECT 1 FROM cfop LIMIT 1").fetchone()
    except Exception:
        return False
    return row is not None


def forward(conn) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO cfop (codigo, descricao, tipo) VALUES (%s,%s,%s)"
            " ON CONFLICT (codigo) DO NOTHING",
            SEED_CFOP,
        )
        cur.executemany(
            "INSERT INTO cst_icms (codigo, descricao) VALUES (%s,%s)"
            " ON CONFLICT (codigo) DO NOTHING",
            SEED_CST_ICMS,
        )
        cur.executemany(
            "INSERT INTO cst_pis (codigo, descricao) VALUES (%s,%s)"
            " ON CONFLICT (codigo) DO NOTHING",
            SEED_CST_PIS,
        )
        cur.executemany(
            "INSERT INTO cst_cofins (codigo, descricao) VALUES (%s,%s)"
            " ON CONFLICT (codigo) DO NOTHING",
            SEED_CST_PIS,  # mesmos códigos do PIS
        )
        cur.executemany(
            "INSERT INTO csosn (codigo, descricao) VALUES (%s,%s)"
            " ON CONFLICT (codigo) DO NOTHING",
            SEED_CSOSN,
        )
        cur.executemany(
            "INSERT INTO beneficios_fiscais (codigo, descricao, tipo, valor_default)"
            " VALUES (%s,%s,%s,%s) ON CONFLICT (codigo) DO NOTHING",
            SEED_BENEFICIOS,
        )
    conn.commit()


def backward(conn) -> None:
    """Remove os seeds de referência (mantém as tabelas)."""
    conn.execute("DELETE FROM cfop")
    conn.execute("DELETE FROM cst_icms")
    conn.execute("DELETE FROM cst_pis")
    conn.execute("DELETE FROM cst_cofins")
    conn.execute("DELETE FROM csosn")
    conn.execute("DELETE FROM beneficios_fiscais")
    conn.commit()
