"""Regras de classificacao de despesas e competencias gerenciais.

O servico mantem a classificacao no backend e grava um snapshot no titulo.
Assim, uma alteracao futura no plano de contas nao reescreve o passado.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from catalog_server.db import system_conn


NATUREZAS = {
    "fixa", "variavel", "custo_direto", "cmv", "nao_rateavel", "fora_precificacao",
}
POLITICAS = {
    "nao_incluir", "ratear_faturamento", "ratear_unidades",
    "ratear_custo_mercadoria", "apropriar_direto", "revisao_manual",
}
STATUS_CLASSIFICACAO = {"pendente", "classificada", "aprovada", "rejeitada"}
COMPONENTES = {"frete", "cartao", "comissao", "embalagem", "outros"}
_COMPETENCIA = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _snapshot_classificacao(row: dict) -> dict:
    """Mantém a auditoria pequena e serializável, sem copiar o título inteiro."""
    keys = (
        "plano_conta_id", "competencia", "natureza_custo_snapshot",
        "politica_rateio_snapshot", "elegivel_precificacao", "componente_precificacao",
        "centro_custo_id", "origem_classificacao", "status_classificacao",
    )
    return {key: row.get(key) for key in keys}


def competencia(value: str | None, fallback: str | None = None) -> str:
    raw = (value or fallback or date.today().isoformat()).strip()
    if len(raw) >= 7:
        raw = raw[:7]
    if not _COMPETENCIA.fullmatch(raw):
        raise ValueError("competencia deve usar o formato YYYY-MM")
    return raw


def _bool(value: Any) -> bool:
    return value is True or value == 1 or str(value).lower() in {"1", "true", "on"}


def obter_conta(conn, conta_id: int | None) -> dict | None:
    if not conta_id:
        return None
    row = conn.execute("SELECT * FROM plano_de_contas WHERE id=?", (int(conta_id),)).fetchone()
    return dict(row) if row else None


def _regra_fornecedor(conn, fornecedor_id: int | None) -> dict | None:
    if not fornecedor_id:
        return None
    row = conn.execute(
        """SELECT r.*, pc.codigo AS conta_codigo, pc.nome AS conta_nome
           FROM fornecedor_regra_financeira r
           JOIN plano_de_contas pc ON pc.id=r.plano_conta_id
          WHERE r.fornecedor_id=? AND r.ativo
            AND (r.vigencia_inicio IS NULL OR r.vigencia_inicio <= CURRENT_DATE)
            AND (r.vigencia_fim IS NULL OR r.vigencia_fim >= CURRENT_DATE)
            AND pc.ativo = 1
          ORDER BY r.prioridade, r.id DESC LIMIT 1""",
        (int(fornecedor_id),),
    ).fetchone()
    return dict(row) if row else None


def validar_conta(conta: dict) -> None:
    if not conta:
        raise ValueError("Plano de contas não encontrado")
    if not _bool(conta.get("ativo", True)):
        raise ValueError("Plano de contas inativo")
    if conta.get("tipo") != "despesa":
        raise ValueError("Conta a pagar deve usar uma conta do tipo despesa")
    natureza = str(conta.get("natureza_custo") or "fora_precificacao")
    politica = str(conta.get("politica_rateio") or "nao_incluir")
    if natureza not in NATUREZAS:
        raise ValueError("Natureza de custo inválida")
    if politica not in POLITICAS:
        raise ValueError("Política de rateio inválida")
    if natureza in {"nao_rateavel", "fora_precificacao"} and politica != "nao_incluir":
        raise ValueError("Natureza não rateável deve usar política não incluir")
    componente = conta.get("componente_variavel")
    if componente and str(componente) not in COMPONENTES:
        raise ValueError("Componente variável inválido")


def preparar_classificacao(
    conn,
    *,
    plano_conta_id: int | None = None,
    fornecedor_id: int | None = None,
    competencia_value: str | None = None,
    centro_custo_id: int | None = None,
    origem: str = "manual",
    exigir: bool = False,
) -> dict:
    """Resolve uma classificacao nova sem alterar o banco.

    Lancamentos legados podem permanecer pendentes durante a migracao. Novos
    formularios devem enviar `exigir=True` para transformar a classificacao
    em obrigatoria sem quebrar consumidores antigos durante o Expand.
    """
    regra = None
    if plano_conta_id is None:
        regra = _regra_fornecedor(conn, fornecedor_id)
        if regra:
            plano_conta_id = int(regra["plano_conta_id"])
            if not centro_custo_id and regra.get("centro_custo_id"):
                centro_custo_id = int(regra["centro_custo_id"])
            if not competencia_value and regra.get("competencia_padrao"):
                competencia_value = str(regra["competencia_padrao"])
            origem = "regra_fornecedor"

    conta = obter_conta(conn, plano_conta_id)
    if conta is None:
        if exigir:
            raise ValueError("Selecione um plano de contas para a despesa")
        return {
            "plano_conta_id": None,
            "competencia": competencia(competencia_value),
            "natureza_custo_snapshot": None,
            "politica_rateio_snapshot": None,
            "elegivel_precificacao": False,
            "componente_precificacao": None,
            "centro_custo_id": centro_custo_id,
            "origem_classificacao": "pendente",
            "status_classificacao": "pendente",
        }

    validar_conta(conta)
    comp = competencia(competencia_value, regra.get("competencia_padrao") if regra else None)
    exige_cc = _bool(conta.get("exige_centro_custo"))
    exige_comp = _bool(conta.get("exige_competencia"))
    if exige_cc and not centro_custo_id:
        raise ValueError("A conta selecionada exige centro de custo")
    if exige_comp and not comp:
        raise ValueError("A conta selecionada exige competência")
    politica = str(conta.get("politica_rateio") or "nao_incluir")
    elegivel = _bool(conta.get("permite_rateio")) and politica != "nao_incluir"
    return {
        "plano_conta_id": int(conta["id"]),
        "competencia": comp,
        "natureza_custo_snapshot": str(conta.get("natureza_custo") or "fora_precificacao"),
        "politica_rateio_snapshot": politica,
        "elegivel_precificacao": elegivel,
        "componente_precificacao": conta.get("componente_variavel"),
        "centro_custo_id": centro_custo_id,
        "origem_classificacao": origem,
        "status_classificacao": "classificada",
    }


def classificar_conta(
    conta_pagar_id: int,
    *,
    plano_conta_id: int,
    competencia_value: str | None,
    centro_custo_id: int | None,
    usuario_id: int | None,
    observacao: str | None = None,
    aprovar: bool = False,
) -> dict:
    with system_conn() as conn:
        row = conn.execute("SELECT * FROM contas_pagar WHERE id=? FOR UPDATE", (conta_pagar_id,)).fetchone()
        if not row:
            raise LookupError("Conta a pagar não encontrada")
        antes = dict(row)
        meta = preparar_classificacao(
            conn,
            plano_conta_id=plano_conta_id,
            fornecedor_id=row["fornecedor_id"],
            competencia_value=competencia_value,
            centro_custo_id=centro_custo_id,
            origem="manual",
            exigir=True,
        )
        status = "aprovada" if aprovar else "classificada"
        conn.execute(
            """UPDATE contas_pagar SET plano_conta_id=?, competencia=?,
               natureza_custo_snapshot=?, politica_rateio_snapshot=?,
               elegivel_precificacao=?, componente_precificacao=?, centro_custo_id=?,
               origem_classificacao='manual', status_classificacao=?,
               classificado_por=?, classificado_em=now(), aprovado_por=CASE WHEN ? THEN ? ELSE NULL END,
               aprovado_em=CASE WHEN ? THEN now() ELSE NULL END,
               observacao_classificacao=? WHERE id=?""",
            (
                meta["plano_conta_id"], meta["competencia"], meta["natureza_custo_snapshot"],
                meta["politica_rateio_snapshot"], meta["elegivel_precificacao"],
                meta["componente_precificacao"], meta["centro_custo_id"], status,
                usuario_id, aprovar, usuario_id, aprovar, observacao or None, conta_pagar_id,
            ),
        )
        result = conn.execute(
            """SELECT cp.*, pc.codigo AS conta_codigo, pc.nome AS conta_nome,
                      pc.natureza_custo, pc.politica_rateio
                 FROM contas_pagar cp LEFT JOIN plano_de_contas pc ON pc.id=cp.plano_conta_id
                WHERE cp.id=?""",
            (conta_pagar_id,),
        ).fetchone()
        from catalog_server.services import infra
        infra.registrar(
            "classificar_conta_pagar",
            "conta_pagar",
            conta_pagar_id,
            antes=_snapshot_classificacao(antes),
            depois=_snapshot_classificacao(dict(result)),
            motivo=observacao,
            ator_id=usuario_id,
            conn=conn,
        )
        return dict(result)


def listar_pendencias(limit: int = 100, offset: int = 0) -> dict:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    with system_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM contas_pagar WHERE status NOT IN ('cancelado','pago') "
            "AND status_classificacao IN ('pendente','rejeitada')"
        ).fetchone()["n"]
        rows = conn.execute(
            """SELECT cp.*, f.nome AS fornecedor_nome, pc.codigo AS conta_codigo,
                      pc.nome AS conta_nome, pc.natureza_custo, pc.politica_rateio
                 FROM contas_pagar cp
                 LEFT JOIN fornecedores f ON f.id=cp.fornecedor_id
                 LEFT JOIN plano_de_contas pc ON pc.id=cp.plano_conta_id
                WHERE cp.status NOT IN ('cancelado','pago')
                  AND cp.status_classificacao IN ('pendente','rejeitada')
                ORDER BY cp.data_vencimento, cp.id LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": int(total or 0), "limit": limit, "offset": offset}


def criar_rateio(
    conta_pagar_id: int,
    itens: list[dict],
    *,
    usuario_id: int | None,
) -> dict:
    if not itens:
        raise ValueError("Informe ao menos uma linha de rateio")
    with system_conn() as conn:
        conta = conn.execute("SELECT * FROM contas_pagar WHERE id=? FOR UPDATE", (conta_pagar_id,)).fetchone()
        if not conta:
            raise LookupError("Conta a pagar não encontrada")
        if not conta["plano_conta_id"]:
            raise ValueError("Classifique a conta antes de ratear")
        total_pct = 0.0
        total_valor = 0.0
        linhas: list[dict] = []
        for item in itens:
            pct = float(item.get("percentual") or 0)
            if pct <= 0 or pct > 100:
                raise ValueError("Percentual de rateio deve estar entre 0 e 100")
            valor = round(float(item.get("valor") if item.get("valor") is not None else float(conta["valor"]) * pct / 100), 2)
            total_pct += pct
            total_valor += valor
            linhas.append({
                "competencia": competencia(item.get("competencia"), conta["competencia"]),
                "centro_custo_id": item.get("centro_custo_id"),
                "produto_id": item.get("produto_id"),
                "percentual": pct,
                "valor": valor,
                "politica_rateio": item.get("politica_rateio") or conta["politica_rateio_snapshot"] or "apropriar_direto",
                "elegivel_precificacao": _bool(item.get("elegivel_precificacao", conta["elegivel_precificacao"])),
            })
            if linhas[-1]["politica_rateio"] not in POLITICAS:
                raise ValueError("Política de rateio inválida")
            if linhas[-1]["elegivel_precificacao"] and linhas[-1]["politica_rateio"] == "nao_incluir":
                raise ValueError("Rateio elegível não pode usar a política não incluir")
            if linhas[-1]["centro_custo_id"]:
                centro = conn.execute(
                    "SELECT ativo FROM centros_custo WHERE id=?",
                    (int(linhas[-1]["centro_custo_id"]),),
                ).fetchone()
                if not centro or not _bool(centro["ativo"]):
                    raise ValueError("Centro de custo do rateio inválido ou inativo")
            if linhas[-1]["produto_id"]:
                produto = conn.execute(
                    "SELECT ativo FROM produtos_cadastro WHERE id=?",
                    (int(linhas[-1]["produto_id"]),),
                ).fetchone()
                if not produto or not _bool(produto["ativo"]):
                    raise ValueError("Produto do rateio inválido ou inativo")
        if abs(total_pct - 100.0) > 0.0001:
            raise ValueError("O rateio deve totalizar exatamente 100%")
        if abs(total_valor - float(conta["valor"])) > 0.02:
            raise ValueError("Os valores do rateio devem totalizar o valor da conta")
        conn.execute("DELETE FROM conta_pagar_rateio WHERE conta_pagar_id=?", (conta_pagar_id,))
        for linha in linhas:
            conn.execute(
                """INSERT INTO conta_pagar_rateio
                   (conta_pagar_id, competencia, centro_custo_id, produto_id,
                    percentual, valor, politica_rateio, elegivel_precificacao, criado_por)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (conta_pagar_id, linha["competencia"], linha["centro_custo_id"], linha["produto_id"],
                 linha["percentual"], linha["valor"], linha["politica_rateio"],
                 linha["elegivel_precificacao"], usuario_id),
            )
        conn.execute(
            "UPDATE contas_pagar SET status_classificacao='classificada', classificado_por=?, classificado_em=now() WHERE id=?",
            (usuario_id, conta_pagar_id),
        )
        from catalog_server.services import infra
        infra.registrar(
            "ratear_conta_pagar",
            "conta_pagar",
            conta_pagar_id,
            antes={"rateio": "substituido"},
            depois={"rateio": linhas},
            ator_id=usuario_id,
            conn=conn,
        )
        return listar_rateio_conn(conn, conta_pagar_id)


def listar_rateio_conn(conn, conta_pagar_id: int) -> dict:
    rows = conn.execute(
        "SELECT * FROM conta_pagar_rateio WHERE conta_pagar_id=? ORDER BY id", (conta_pagar_id,)
    ).fetchall()
    return {"conta_pagar_id": conta_pagar_id, "items": [dict(row) for row in rows]}


def listar_rateio(conta_pagar_id: int) -> dict:
    with system_conn() as conn:
        return listar_rateio_conn(conn, conta_pagar_id)


def memoria_classificacao(conta_pagar_id: int) -> dict:
    """Retorna a classificação efetivamente usada e o rateio do título."""
    with system_conn() as conn:
        row = conn.execute(
            """SELECT cp.id, cp.fornecedor, cp.fornecedor_id, cp.descricao, cp.valor,
                      cp.competencia, cp.plano_conta_id, cp.natureza_custo_snapshot,
                      cp.politica_rateio_snapshot, cp.elegivel_precificacao,
                      cp.componente_precificacao, cp.centro_custo_id,
                      cp.origem_classificacao, cp.status_classificacao,
                      pc.codigo AS conta_codigo, pc.nome AS conta_nome
                 FROM contas_pagar cp LEFT JOIN plano_de_contas pc ON pc.id=cp.plano_conta_id
                WHERE cp.id=?""",
            (conta_pagar_id,),
        ).fetchone()
        if not row:
            raise LookupError("Conta a pagar não encontrada")
        return {"conta": dict(row), "rateio": listar_rateio_conn(conn, conta_pagar_id)["items"]}


def criar_competencia(data: dict, usuario_id: int | None) -> dict:
    comp = competencia(data.get("competencia"))
    faturamento = float(data.get("faturamento_base") or 0)
    if faturamento < 0:
        raise ValueError("faturamento_base inválido")
    fonte = data.get("faturamento_fonte") or "realizado"
    criterio = data.get("criterio_apuracao") or "competencia"
    if fonte not in {"realizado", "planejado", "media_movel", "manual"}:
        raise ValueError("faturamento_fonte inválido")
    if criterio not in {"competencia", "caixa", "gerencial", "planejado"}:
        raise ValueError("criterio_apuracao inválido")
    with system_conn() as conn:
        conn.execute(
            """INSERT INTO precificacao_competencia
               (competencia, faturamento_base, faturamento_fonte, criterio_apuracao, observacao, criado_por)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT (competencia) DO UPDATE SET
                 faturamento_base=EXCLUDED.faturamento_base,
                 faturamento_fonte=EXCLUDED.faturamento_fonte,
                 criterio_apuracao=EXCLUDED.criterio_apuracao,
                 observacao=EXCLUDED.observacao,
                 atualizado_em=now()""",
            (comp, faturamento, fonte, criterio, str(data.get("observacao") or ""), usuario_id),
        )
        row = conn.execute("SELECT * FROM precificacao_competencia WHERE competencia=?", (comp,)).fetchone()
        return dict(row)


def listar_competencias() -> list[dict]:
    with system_conn() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM precificacao_competencia ORDER BY competencia DESC"
        ).fetchall()]


def obter_regra_fornecedor(fornecedor_id: int) -> dict | None:
    with system_conn() as conn:
        row = conn.execute(
            """SELECT r.*, pc.codigo AS conta_codigo, pc.nome AS conta_nome,
                      pc.natureza_custo, pc.politica_rateio
                 FROM fornecedor_regra_financeira r
                 JOIN plano_de_contas pc ON pc.id=r.plano_conta_id
                WHERE r.fornecedor_id=? ORDER BY r.id DESC LIMIT 1""",
            (fornecedor_id,),
        ).fetchone()
        return dict(row) if row else None


def salvar_regra_fornecedor(fornecedor_id: int, data: dict, usuario_id: int | None) -> dict:
    plano_id = int(data["plano_conta_id"])
    comp = competencia(data.get("competencia_padrao")) if data.get("competencia_padrao") else None
    prioridade = int(data.get("prioridade") or 100)
    if prioridade < 0:
        raise ValueError("prioridade inválida")
    with system_conn() as conn:
        conta = obter_conta(conn, plano_id)
        validar_conta(conta or {})
        if data.get("centro_custo_id"):
            cc = conn.execute("SELECT ativo FROM centros_custo WHERE id=?", (int(data["centro_custo_id"]),)).fetchone()
            if not cc or not _bool(cc["ativo"]):
                raise ValueError("Centro de custo inválido ou inativo")
        conn.execute(
            """INSERT INTO fornecedor_regra_financeira
               (fornecedor_id, plano_conta_id, centro_custo_id, competencia_padrao,
                prioridade, ativo, vigencia_inicio, vigencia_fim, criado_por, atualizado_por, atualizado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,now())
               ON CONFLICT (fornecedor_id) DO UPDATE SET
                 plano_conta_id=EXCLUDED.plano_conta_id,
                 centro_custo_id=EXCLUDED.centro_custo_id,
                 competencia_padrao=EXCLUDED.competencia_padrao,
                 prioridade=EXCLUDED.prioridade,
                 ativo=EXCLUDED.ativo,
                 vigencia_inicio=EXCLUDED.vigencia_inicio,
                 vigencia_fim=EXCLUDED.vigencia_fim,
                 atualizado_por=EXCLUDED.atualizado_por,
                 atualizado_em=now()""",
            (fornecedor_id, plano_id, data.get("centro_custo_id"), comp, prioridade,
             _bool(data.get("ativo", True)), data.get("vigencia_inicio"), data.get("vigencia_fim"),
             usuario_id, usuario_id),
        )
        row = conn.execute(
            """SELECT r.*, pc.codigo AS conta_codigo, pc.nome AS conta_nome,
                      pc.natureza_custo, pc.politica_rateio
                 FROM fornecedor_regra_financeira r JOIN plano_de_contas pc ON pc.id=r.plano_conta_id
                WHERE r.fornecedor_id=?""",
            (fornecedor_id,),
        ).fetchone()
        return dict(row)


def apurar_competencia(competencia_value: str) -> dict:
    comp = competencia(competencia_value)
    with system_conn() as conn:
        base = conn.execute("SELECT * FROM precificacao_competencia WHERE competencia=?", (comp,)).fetchone()
        if not base:
            raise LookupError("Competência não encontrada")
        sem_rateio = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN natureza_custo_snapshot='fixa' THEN valor ELSE 0 END),0) AS fixas,
                      COALESCE(SUM(CASE WHEN natureza_custo_snapshot='variavel' THEN valor ELSE 0 END),0) AS variaveis,
                      COALESCE(SUM(CASE WHEN natureza_custo_snapshot='custo_direto' THEN valor ELSE 0 END),0) AS diretos
                FROM contas_pagar cp
                WHERE cp.competencia=? AND cp.elegivel_precificacao
                  AND cp.status_classificacao IN ('classificada','aprovada')
                  AND cp.status NOT IN ('cancelado')
                  AND NOT EXISTS (SELECT 1 FROM conta_pagar_rateio r WHERE r.conta_pagar_id=cp.id)""",
            (comp,),
        ).fetchone()
        rateado = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN cp.natureza_custo_snapshot='fixa' THEN r.valor ELSE 0 END),0) AS fixas,
                      COALESCE(SUM(CASE WHEN cp.natureza_custo_snapshot='variavel' THEN r.valor ELSE 0 END),0) AS variaveis,
                      COALESCE(SUM(CASE WHEN cp.natureza_custo_snapshot='custo_direto' THEN r.valor ELSE 0 END),0) AS diretos
                FROM conta_pagar_rateio r JOIN contas_pagar cp ON cp.id=r.conta_pagar_id
                WHERE r.competencia=? AND r.elegivel_precificacao
                  AND cp.status_classificacao IN ('classificada','aprovada')
                  AND cp.status NOT IN ('cancelado')""",
            (comp,),
        ).fetchone()
        pendentes = conn.execute(
            """SELECT COUNT(*) AS n FROM contas_pagar
                WHERE competencia=? AND status NOT IN ('cancelado','pago')
                  AND status_classificacao IN ('pendente','rejeitada')""",
            (comp,),
        ).fetchone()["n"]
    fixas = round(float(sem_rateio["fixas"] or 0) + float(rateado["fixas"] or 0), 2)
    variaveis = round(float(sem_rateio["variaveis"] or 0) + float(rateado["variaveis"] or 0), 2)
    diretos = round(float(sem_rateio["diretos"] or 0) + float(rateado["diretos"] or 0), 2)
    faturamento = float(base["faturamento_base"] or 0)
    return {
        "competencia": comp,
        "status": base["status"],
        "faturamento_base": faturamento,
        "despesas_fixas": fixas,
        "despesas_variaveis": variaveis,
        "custos_diretos": diretos,
        "despesa_fixa_pct": round(fixas / faturamento * 100, 4) if faturamento else None,
        "despesa_variavel_pct": round(variaveis / faturamento * 100, 4) if faturamento else None,
        "pendencias_classificacao": int(pendentes or 0),
    }


def apuracao_para_precificacao(competencia_value: str | None = None) -> dict | None:
    """Retorna somente uma competencia aprovada/fechada para o motor."""
    with system_conn() as conn:
        if competencia_value:
            comp = competencia(competencia_value)
            row = conn.execute(
                "SELECT status FROM precificacao_competencia WHERE competencia=? "
                "AND status IN ('aprovada','fechada')", (comp,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT competencia FROM precificacao_competencia "
                "WHERE status IN ('aprovada','fechada') ORDER BY competencia DESC LIMIT 1"
            ).fetchone()
            comp = str(row["competencia"]) if row else None
        if not row or not comp:
            return None
    return apurar_competencia(comp)


def alterar_status_competencia(competencia_value: str, status: str, usuario_id: int | None, motivo: str | None = None) -> dict:
    comp = competencia(competencia_value)
    if status not in {"aprovada", "fechada", "reaberta"}:
        raise ValueError("Status de competência inválido")
    with system_conn() as conn:
        row = conn.execute("SELECT id FROM precificacao_competencia WHERE competencia=? FOR UPDATE", (comp,)).fetchone()
        if not row:
            raise LookupError("Competência não encontrada")
        atual = conn.execute("SELECT * FROM precificacao_competencia WHERE competencia=?", (comp,)).fetchone()
        status_atual = str(atual["status"])
        transicoes = {
            "aprovada": {"aberta", "em_revisao", "reaberta"},
            "fechada": {"aprovada"},
            "reaberta": {"fechada"},
        }
        if status_atual not in transicoes[status]:
            raise ValueError(f"Transição de competência inválida: {status_atual} → {status}")
        if status == "reaberta" and not (motivo or "").strip():
            raise ValueError("Informe o motivo para reabrir a competência")
        if status in {"aprovada", "fechada"}:
            pendentes = conn.execute(
                """SELECT COUNT(*) AS n FROM contas_pagar
                    WHERE competencia=? AND status NOT IN ('cancelado','pago')
                      AND status_classificacao IN ('pendente','rejeitada')""",
                (comp,),
            ).fetchone()["n"]
            if pendentes:
                raise ValueError("Existem contas pendentes de classificação na competência")
        conn.execute(
            """UPDATE precificacao_competencia SET status=?, observacao=COALESCE(NULLIF(?, ''), observacao),
               aprovado_por=CASE WHEN ?='aprovada' THEN ? ELSE aprovado_por END,
               aprovado_em=CASE WHEN ?='aprovada' THEN now() ELSE aprovado_em END,
               fechado_por=CASE WHEN ?='fechada' THEN ? ELSE fechado_por END,
               fechado_em=CASE WHEN ?='fechada' THEN now() ELSE fechado_em END,
               atualizado_em=now() WHERE competencia=?""",
            (status, motivo or "", status, usuario_id, status, status, usuario_id, status, comp),
        )
        row = conn.execute("SELECT * FROM precificacao_competencia WHERE competencia=?", (comp,)).fetchone()
        from catalog_server.services import infra
        infra.registrar(
            "alterar_status_competencia",
            "precificacao_competencia",
            comp,
            antes={"competencia": comp, "status": status_atual, "faturamento_base": float(atual["faturamento_base"] or 0)},
            depois={"competencia": comp, "status": status, "faturamento_base": float(row["faturamento_base"] or 0)},
            motivo=motivo,
            ator_id=usuario_id,
            conn=conn,
        )
        return dict(row)
