"""XYZ e matriz de política (COM-002): variabilidade/intermitência da demanda
a partir do histórico mensal de vendas finalizadas, cruzando ABC×XYZ para
sugerir política de estoque/contagem/serviço. Limiares configuráveis e auditados.
"""

from __future__ import annotations

import json
import math

from catalog_server.db import system_conn


def _config() -> dict:
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM xyz_config WHERE id=1").fetchone()
    if not row:
        return {"cv_x": 0.5, "cv_y": 1.0, "meses_historico": 6, "intermitente_zeros_pct": 0.5}
    return dict(row)


def atualizar_config(cv_x: float, cv_y: float, meses_historico: int, intermitente_zeros_pct: float, usuario_id: int | None = None) -> dict:
    with system_conn() as conn:
        conn.execute(
            "INSERT INTO xyz_config (id, cv_x, cv_y, meses_historico, intermitente_zeros_pct, atualizado_por, atualizado_em)"
            " VALUES (1,?,?,?,?,?,NOW())"
            " ON CONFLICT (id) DO UPDATE SET cv_x=EXCLUDED.cv_x, cv_y=EXCLUDED.cv_y,"
            " meses_historico=EXCLUDED.meses_historico, intermitente_zeros_pct=EXCLUDED.intermitente_zeros_pct,"
            " atualizado_por=EXCLUDED.atualizado_por, atualizado_em=NOW()",
            (cv_x, cv_y, int(meses_historico), intermitente_zeros_pct, usuario_id),
        )
    return _config()


def _vendas_mensais(produto_id: int, meses: int) -> list[float]:
    """Quantidade vendida por mês (vendas finalizadas, últimos N meses)."""
    with system_conn() as conn:
        rows = conn.execute(
            """
            SELECT SUBSTR(o.criado_em,1,7) AS mes, SUM(oi.quantidade) AS qtd
            FROM orcamento_itens oi
            JOIN orcamentos o ON o.id=oi.orcamento_id
            WHERE o.status='finalizado' AND oi.produto_id=?
              AND SUBSTR(o.criado_em,1,10) >= to_char(CURRENT_DATE - (%s::int * interval '1 month'), 'YYYY-MM-DD')
            GROUP BY mes ORDER BY mes
            """,
            (produto_id, meses),
        ).fetchall()
    # garante N posições (meses sem venda = 0)
    with system_conn() as conn:
        r2 = conn.execute(
            "SELECT to_char(generate_series(CURRENT_DATE - (%s::int * interval '1 month') + interval '1 day', CURRENT_DATE, interval '1 month'), 'YYYY-MM') AS mes",
            (meses,),
        ).fetchall()
    mapa = {r["mes"]: float(r["qtd"]) for r in rows}
    return [mapa.get(r["mes"], 0.0) for r in r2]


def classificar(produto_id: int) -> dict:
    cfg = _config()
    meses = int(cfg["meses_historico"] or 6)
    serie = _vendas_mensais(produto_id, meses)
    media = sum(serie) / len(serie) if serie else 0.0
    if len(serie) > 1:
        variancia = sum((x - media) ** 2 for x in serie) / (len(serie) - 1)
        desvio = math.sqrt(variancia)
    else:
        desvio = 0.0
    cv = (desvio / media) if media > 0 else 0.0
    zeros = sum(1 for x in serie if x == 0)
    intermitente = (zeros / len(serie)) >= float(cfg["intermitente_zeros_pct"] or 0.5) if serie else False

    if intermitente or media <= 0:
        classe = "Z"
    elif cv <= float(cfg["cv_x"] or 0.5):
        classe = "X"
    elif cv <= float(cfg["cv_y"] or 1.0):
        classe = "Y"
    else:
        classe = "Z"

    with system_conn() as conn:
        conn.execute(
            "UPDATE produtos_cadastro SET classe_xyz=?, cv_demanda=?, intermitente=?, xyz_calculado_em=NOW() WHERE id=?",
            (classe, round(cv, 4), intermitente, produto_id),
        )
    return {"produto_id": produto_id, "classe_xyz": classe, "cv": round(cv, 4),
            "intermitente": intermitente, "media_mensal": round(media, 3), "serie": serie}


def calcular_todos() -> dict:
    with system_conn() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM produtos_cadastro").fetchall()]
    cont = {"X": 0, "Y": 0, "Z": 0}
    for pid in ids:
        r = classificar(pid)
        cont[r["classe_xyz"]] += 1
    return {"produtos": len(ids), "por_classe": cont}


MATRIZ: dict[tuple[str, str], dict[str, str]] = {
    ("A", "X"): {"estoque": "alta disponibilidade", "contagem": "frequente", "servico": "alto"},
    ("A", "Y"): {"estoque": "segurança + ponto pedido", "contagem": "periodica", "servico": "alto"},
    ("A", "Z"): {"estoque": "sob encomenda", "contagem": "periodica", "servico": "medio"},
    ("B", "X"): {"estoque": "ponto de pedido", "contagem": "periodica", "servico": "medio"},
    ("B", "Y"): {"estoque": "ponto de pedido", "contagem": "periodica", "servico": "medio"},
    ("B", "Z"): {"estoque": "sob encomenda", "contagem": "anual", "servico": "medio"},
    ("C", "X"): {"estoque": "mínimo/máximo", "contagem": "anual", "servico": "baixo"},
    ("C", "Y"): {"estoque": "mínimo/máximo", "contagem": "anual", "servico": "baixo"},
    ("C", "Z"): {"estoque": "sob encomenda", "contagem": "sob demanda", "servico": "baixo"},
}


def matriz_politica(abc: str, xyz: str) -> dict:
    return MATRIZ.get((abc.upper(), xyz.upper()), MATRIZ[("C", "Z")])


def resumo_matriz() -> dict:
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT COALESCE(classe_abc,'') AS abc, COALESCE(classe_xyz,'') AS xyz, COUNT(*) AS produtos"
            " FROM produtos_cadastro GROUP BY abc, xyz ORDER BY abc, xyz"
        ).fetchall()
    return {"celulas": [dict(r) for r in rows]}


def config_json() -> str:
    return json.dumps(_config())