"""Lançamentos parcelados e recorrentes (v2.25.0) — modelo TOTVS/desdobramento.

Um lançamento gera N títulos:
- `condicao`: usa `condicao_parcelas` (dias + percentual) a partir da emissão;
- `manual`: N parcelas com intervalo fixo de dias, valor total dividido;
- `datas`: lista explícita de {valor, vencimento};
- recorrência: frequência fixa (mensal/semanal/anual), N ocorrências geradas
  antecipadamente com valor integral cada.

Todas as parcelas de um lançamento compartilham `grupo_id` (uuid) e carregam
`parcela i/N` + `origem_tipo/origem_id` quando aplicável.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from catalog_server.db import system_conn
from catalog_server.repositories import condicao_repo

FREQUENCIAS = ("mensal", "semanal", "anual")


def novo_grupo() -> str:
    return uuid.uuid4().hex[:12]


def _add_mes(d: date, meses: int) -> date:
    """Soma meses sem perder fim-de-mês (31/01 + 1 = 28/02)."""
    mes = d.month - 1 + meses
    ano = d.year + mes // 12
    mes = mes % 12 + 1
    dia = min(d.day, [31, 29 if ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return date(ano, mes, dia)


def calcular_parcelas(
    modo: str,
    valor_total: float,
    data_base: str,
    condicao_id: int | None = None,
    n_parcelas: int = 1,
    intervalo_dias: int = 30,
    datas: list[dict] | None = None,
) -> list[dict]:
    """Calcula as parcelas [{valor, vencimento, dias}] sem gravar (preview)."""
    base = date.fromisoformat(str(data_base)[:10])
    if modo == "condicao":
        if not condicao_id:
            raise ValueError("Informe a condição de pagamento")
        parcelas = condicao_repo.list_parcelas(int(condicao_id))
        if not parcelas:
            raise ValueError("Condição sem parcelas cadastradas")
        out = []
        for p in parcelas:
            pct = float(p.get("percentual") or 0)
            dias = int(p.get("dias") or 0)
            out.append({
                "valor": round(valor_total * pct / 100.0, 2),
                "vencimento": (base + timedelta(days=dias)).isoformat(),
                "dias": dias,
            })
        # ajusta a última para cobrir arredondamento
        dif = round(valor_total - sum(x["valor"] for x in out), 2)
        if abs(dif) > 0.005 and out:
            out[-1]["valor"] = round(out[-1]["valor"] + dif, 2)
        return out

    if modo == "manual":
        n = max(1, int(n_parcelas or 1))
        intervalo = max(0, int(intervalo_dias or 0))
        valor = round(valor_total / n, 2)
        out = [{"valor": valor, "vencimento": (base + timedelta(days=intervalo * i)).isoformat(),
                "dias": intervalo * i} for i in range(n)]
        dif = round(valor_total - valor * n, 2)
        if abs(dif) > 0.005:
            out[-1]["valor"] = round(out[-1]["valor"] + dif, 2)
        return out

    if modo == "datas":
        lista = datas or []
        if not lista:
            raise ValueError("Informe as parcelas (valor + vencimento)")
        out = []
        for d in lista:
            v = round(float(d.get("valor") or 0), 2)
            if v <= 0:
                continue
            out.append({"valor": v, "vencimento": str(d.get("vencimento") or "")[:10], "dias": 0})
        if not out:
            raise ValueError("Nenhuma parcela válida informada")
        return out

    raise ValueError(f"modo inválido: {modo}")


def calcular_recorrencia(
    frequencia: str,
    valor: float,
    primeira: str,
    n_ocorrencias: int,
    dia: int | None = None,
) -> list[dict]:
    """Gera as ocorrências antecipadas [{valor, vencimento}]."""
    if frequencia not in FREQUENCIAS:
        raise ValueError(f"frequência inválida: {frequencia}")
    n = max(1, int(n_ocorrencias or 1))
    d = date.fromisoformat(str(primeira)[:10])
    if dia:
        d = _add_mes(d.replace(day=1), 0).replace(day=min(int(dia), 28)) if frequencia == "mensal" else d
    out = []
    for i in range(n):
        if frequencia == "mensal":
            venc = _add_mes(d, i) if i > 0 or not dia else d
            if dia:
                venc = _add_mes(d.replace(day=min(int(dia), 28)), i)
        elif frequencia == "semanal":
            venc = d + timedelta(weeks=i)
        else:  # anual
            venc = _add_mes(d, 12 * i)
        out.append({"valor": round(valor, 2), "vencimento": venc.isoformat(), "dias": 0})
    return out


def criar_lote(
    tabela: str,
    dados: dict,
    parcelas: list[dict],
) -> tuple[list[int], str]:
    """Grava as parcelas na tabela (`contas_pagar`/`contas_receber`).

    Retorna (ids criados, grupo_id). Todas recebem o mesmo grupo_id e parcela i/N.
    """
    if tabela not in ("contas_pagar", "contas_receber"):
        raise ValueError("tabela inválida")
    grupo = novo_grupo()
    n = len(parcelas)
    pessoa_campo = "fornecedor" if tabela == "contas_pagar" else "cliente"
    pessoa_id_campo = "fornecedor_id" if tabela == "contas_pagar" else "cliente_id"
    ids: list[int] = []
    with system_conn() as conn:
        classificacao = None
        if tabela == "contas_pagar":
            from catalog_server.services import classificacao_financeira

            classificacao = classificacao_financeira.preparar_classificacao(
                conn,
                plano_conta_id=dados.get("plano_conta_id"),
                fornecedor_id=dados.get(pessoa_id_campo),
                competencia_value=dados.get("competencia") or dados.get("data_emissao"),
                centro_custo_id=dados.get("centro_custo_id"),
                origem=dados.get("origem_classificacao") or "manual",
                exigir=bool(dados.get("exigir_classificacao")),
            )
        for i, p in enumerate(parcelas, start=1):
            descricao = dados.get("descricao") or ""
            if n > 1:
                descricao = f"{descricao} — parcela {i}/{n}".strip(" —")
            if tabela == "contas_pagar":
                cur = conn.execute(
                    """INSERT INTO contas_pagar
                          (fornecedor, fornecedor_id, descricao, valor, saldo,
                           data_vencimento, data_emissao, plano_conta_id, documento,
                           observacao, competencia, natureza_custo_snapshot,
                           politica_rateio_snapshot, elegivel_precificacao,
                           componente_precificacao, centro_custo_id, origem_classificacao,
                           status_classificacao, origem_tipo, origem_id, parcela,
                           total_parcelas, grupo_id, recorrencia)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        (dados.get(pessoa_campo) or "").strip(),
                        dados.get(pessoa_id_campo),
                        descricao,
                        float(p["valor"]),
                        float(p["valor"]),
                        p["vencimento"],
                        (dados.get("data_emissao") or date.today().isoformat())[:10],
                        classificacao["plano_conta_id"],
                        dados.get("documento") or None,
                        dados.get("observacao") or None,
                        classificacao["competencia"],
                        classificacao["natureza_custo_snapshot"],
                        classificacao["politica_rateio_snapshot"],
                        classificacao["elegivel_precificacao"],
                        classificacao["componente_precificacao"],
                        classificacao["centro_custo_id"],
                        classificacao["origem_classificacao"],
                        classificacao["status_classificacao"],
                        dados.get("origem_tipo") or "manual",
                        dados.get("origem_id"),
                        i,
                        n,
                        grupo,
                        dados.get("recorrencia") or "",
                    ),
                )
            else:
                cur = conn.execute(
                    """INSERT INTO contas_receber
                          (cliente, cliente_id, descricao, valor, saldo,
                           data_vencimento, data_emissao, plano_conta_id, documento,
                           observacao, origem_tipo, origem_id, parcela,
                           total_parcelas, grupo_id, recorrencia)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        (dados.get(pessoa_campo) or "").strip(),
                        dados.get(pessoa_id_campo),
                        descricao,
                        float(p["valor"]),
                        float(p["valor"]),
                        p["vencimento"],
                        (dados.get("data_emissao") or date.today().isoformat())[:10],
                        dados.get("plano_conta_id"),
                        dados.get("documento") or None,
                        dados.get("observacao") or None,
                        dados.get("origem_tipo") or "manual",
                        dados.get("origem_id"),
                        i,
                        n,
                        grupo,
                        dados.get("recorrencia") or "",
                    ),
                )
            ids.append(int(cur.lastrowid))
        conn.commit()
    return ids, grupo


def excluir_lote(tabela: str, grupo_id: str) -> int:
    """Exclui as parcelas EM ABERTO do grupo (pagas/recebidas ficam)."""
    if tabela not in ("contas_pagar", "contas_receber"):
        raise ValueError("tabela inválida")
    with system_conn() as conn:
        cur = conn.execute(
            f"DELETE FROM {tabela} WHERE grupo_id=? AND status IN ('aberto','parcial')",
            (grupo_id,),
        )
        conn.commit()
        return cur.rowcount


def listar_lote(tabela: str, grupo_id: str) -> list[dict]:
    if tabela not in ("contas_pagar", "contas_receber"):
        raise ValueError("tabela inválida")
    with system_conn() as conn:
        return [dict(r) for r in conn.execute(
            f"SELECT * FROM {tabela} WHERE grupo_id=? ORDER BY parcela",
            (grupo_id,),
        ).fetchall()]
