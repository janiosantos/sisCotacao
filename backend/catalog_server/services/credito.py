"""Serviço de crediário: aprovação, exposição e decisões auditáveis."""
from __future__ import annotations

from datetime import date
import json

from catalog_server.db import system_conn
from catalog_server.services import infra

CLIENTE_PADRAO_ID = 1
STATUS_VALIDOS = {
    "nao_solicitado", "em_analise", "aprovado", "suspenso", "reprovado", "expirado", "bloqueado",
}


def _today() -> date:
    return date.today()


def _exigir(actor_id: int | None, acao: str) -> None:
    from catalog_server import permissao

    if not actor_id or not permissao.tem_permissao(actor_id, "credito", acao):
        raise PermissionError("Usuário não possui permissão para esta operação de crédito")


def _dict(row) -> dict | None:
    return dict(row) if row else None


def _snapshot(row) -> dict:
    if not row:
        return {}
    return {
        "id": row.get("id"),
        "cliente_id": row.get("cliente_id"),
        "status": row.get("status"),
        "limite_aprovado": float(row.get("limite_aprovado") or 0),
        "prazo_maximo_dias": int(row.get("prazo_maximo_dias") or 0),
        "vigencia_inicio": str(row.get("vigencia_inicio")) if row.get("vigencia_inicio") else None,
        "vigencia_fim": str(row.get("vigencia_fim")) if row.get("vigencia_fim") else None,
        "versao": int(row.get("versao") or 0),
    }


def _with_conn(_conn, fn):
    if _conn is not None:
        return fn(_conn)
    with system_conn() as conn:
        return fn(conn)


def _get_credito(conn, cliente_id: int, lock: bool = False) -> dict | None:
    suffix = " FOR UPDATE" if lock else ""
    row = conn.execute(
        "SELECT * FROM credito_aprovacao WHERE cliente_id=?" + suffix, (cliente_id,)
    ).fetchone()
    return _dict(row)


def _ensure_credito(conn, cliente_id: int, actor_id: int | None = None) -> dict:
    cliente = conn.execute(
        "SELECT id, nome, ativo FROM clientes WHERE id=?", (cliente_id,)
    ).fetchone()
    if not cliente:
        raise LookupError("Cliente não encontrado")
    if not cliente["ativo"]:
        raise ValueError("Cliente inativo não pode ter crediário")
    conn.execute(
        "INSERT INTO credito_aprovacao (cliente_id, status, created_by, updated_by) VALUES (?, 'nao_solicitado', ?, ?) "
        "ON CONFLICT (cliente_id) DO NOTHING",
        (cliente_id, actor_id, actor_id),
    )
    credito = _get_credito(conn, cliente_id, lock=True)
    if not credito:
        raise RuntimeError("Não foi possível criar o registro de crediário")
    return credito


def _exposicao(conn, cliente_id: int) -> tuple[float, float, float]:
    abertas = conn.execute(
        "SELECT COALESCE(SUM(saldo),0) AS total FROM contas_receber "
        "WHERE cliente_id=? AND status IN ('aberto','parcial')", (cliente_id,)
    ).fetchone()
    atraso = conn.execute(
        "SELECT COALESCE(SUM(saldo),0) AS total FROM contas_receber "
        "WHERE cliente_id=? AND status IN ('aberto','parcial') "
        "AND NULLIF(data_vencimento, '')::date < CURRENT_DATE", (cliente_id,)
    ).fetchone()
    reservas = conn.execute(
        "SELECT COALESCE(SUM(valor),0) AS total FROM credito_reserva "
        "WHERE cliente_id=? AND status='reservada' AND expira_em > NOW()", (cliente_id,)
    ).fetchone()
    return (
        max(0.0, float(abertas["total"] or 0)),
        max(0.0, float(atraso["total"] or 0)),
        max(0.0, float(reservas["total"] or 0)),
    )


def consultar(cliente_id: int, total: float | None = None, _conn=None, lock: bool = False) -> dict | None:
    def run(conn):
        cliente = conn.execute("SELECT id, nome, ativo, limite_credito FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        if not cliente:
            return None
        credito = _get_credito(conn, cliente_id, lock=lock)
        contas, atraso, reservas = _exposicao(conn, cliente_id)
        hoje = _today()
        aprovado = credito and credito.get("status") == "aprovado"
        expirado = bool(aprovado and credito.get("vigencia_fim") and credito["vigencia_fim"] < hoje)
        status = "expirado" if expirado else (credito.get("status") if credito else "nao_solicitado")
        limite = float(credito.get("limite_aprovado") or 0) if credito and not expirado else 0.0
        exposicao = contas + reservas
        disponivel = max(0.0, limite - exposicao)
        valor = max(0.0, float(total or 0))
        return {
            "cliente_id": cliente_id,
            "cliente": cliente["nome"],
            "status": status,
            "aprovado": status == "aprovado",
            "limite_cadastrado": round(max(0.0, float(cliente["limite_credito"] or 0)), 2),
            "limite_aprovado": round(limite, 2),
            "limite_utilizado": round(exposicao, 2),
            "limite_disponivel": round(disponivel, 2),
            "saldo_em_atraso": round(atraso, 2),
            "tem_atraso": atraso > 0.005,
            "excede_limite": status != "aprovado" or valor > disponivel + 0.005,
            "excede_por_atraso": atraso > 0.005 and valor > 0.005,
            "prazo_maximo_dias": int(credito.get("prazo_maximo_dias") or 0) if credito else 0,
            "condicoes_permitidas": credito.get("condicoes_permitidas") or [] if credito else [],
            "vigencia_inicio": str(credito.get("vigencia_inicio")) if credito and credito.get("vigencia_inicio") else None,
            "vigencia_fim": str(credito.get("vigencia_fim")) if credito and credito.get("vigencia_fim") else None,
            "versao": int(credito.get("versao") or 0) if credito else 0,
        }
    return _with_conn(_conn, run)


def validar_venda_a_prazo(cliente_id: int | None, total: float, prazo_dias: int = 0,
                          bloquear_atraso: bool = True, condicao_id: int | None = None,
                          _conn=None) -> dict:
    if cliente_id is None or int(cliente_id) == CLIENTE_PADRAO_ID:
        return {"permitido": False, "code": "cliente_padrao_somente_avista", "motivos": ["Cliente padrão só pode comprar à vista"]}
    if float(total) <= 0:
        return {"permitido": False, "code": "valor_invalido", "motivos": ["Valor da venda deve ser positivo"]}

    def run(conn):
        situacao = consultar(int(cliente_id), total=total, _conn=conn, lock=True)
        if situacao is None:
            return {"permitido": False, "code": "cliente_nao_encontrado", "motivos": ["Cliente não encontrado"]}
        if situacao["status"] != "aprovado":
            code = {
                "expirado": "credito_expirado",
                "bloqueado": "credito_bloqueado",
                "suspenso": "credito_suspenso",
            }.get(situacao["status"], "crediario_nao_aprovado")
            return {"permitido": False, "code": code, "situacao": situacao, "motivos": [f"Crediário com status {situacao['status']}"]}
        if prazo_dias > int(situacao["prazo_maximo_dias"] or 0):
            return {"permitido": False, "code": "prazo_credito_excedido", "situacao": situacao, "motivos": ["Prazo excede o aprovado"]}
        permitidas = situacao.get("condicoes_permitidas") or []
        if permitidas and str(condicao_id) not in {str(item) for item in permitidas}:
            return {"permitido": False, "code": "condicao_credito_nao_permitida", "situacao": situacao, "motivos": ["Condição não está autorizada no crediário"]}
        if bloquear_atraso and situacao["excede_por_atraso"]:
            return {"permitido": False, "code": "cliente_atraso", "situacao": situacao, "motivos": ["Cliente possui parcelas vencidas"]}
        if situacao["excede_limite"]:
            return {"permitido": False, "code": "sem_credito", "situacao": situacao, "motivos": ["Venda excede o limite disponível"]}
        return {"permitido": True, "code": "ok", "situacao": situacao, "motivos": []}
    return _with_conn(_conn, run)


def _registrar_evento(conn, antes: dict, depois: dict, tipo: str, motivo: str,
                      actor_id: int | None, ip: str | None, correlation_id: str | None) -> None:
    conn.execute(
        "INSERT INTO credito_evento (credito_id, cliente_id, tipo_evento, status_anterior, status_novo, "
        "limite_anterior, limite_novo, motivo, snapshot_json, usuario_id, ip, correlation_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (depois["id"], depois["cliente_id"], tipo, antes.get("status"), depois.get("status"),
         antes.get("limite_aprovado"), depois.get("limite_aprovado"), motivo or None,
         json.dumps({"antes": antes, "depois": depois}, default=str), actor_id, ip, correlation_id),
    )
    infra.registrar(
        f"credito_{tipo}", "cliente", depois["cliente_id"], antes=antes, depois=depois,
        motivo=motivo, ator_id=actor_id, ip=ip, correlation_id=correlation_id, conn=conn,
    )


def solicitar(cliente_id: int, motivo: str, actor_id: int, ip: str | None = None, correlation_id: str | None = None) -> dict:
    _exigir(actor_id, "cadastrar")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("Motivo da solicitação é obrigatório")
    with system_conn() as conn:
        antes_row = _ensure_credito(conn, cliente_id, actor_id)
        antes = _snapshot(antes_row)
        conn.execute("UPDATE credito_aprovacao SET status='em_analise', updated_by=?, updated_at=NOW(), versao=versao+1 WHERE id=?", (actor_id, antes_row["id"]))
        depois = _snapshot(_get_credito(conn, cliente_id, lock=True))
        _registrar_evento(conn, antes, depois, "solicitacao", motivo, actor_id, ip, correlation_id)
        return depois


def aprovar(cliente_id: int, limite_aprovado: float, prazo_maximo_dias: int, vigencia_inicio: str,
            vigencia_fim: str, motivo: str, actor_id: int, ip: str | None = None,
            correlation_id: str | None = None, condicoes_permitidas=None) -> dict:
    _exigir(actor_id, "aprovar")
    if limite_aprovado <= 0:
        raise ValueError("Limite aprovado deve ser maior que zero")
    if prazo_maximo_dias < 0:
        raise ValueError("Prazo máximo inválido")
    if not motivo or not motivo.strip():
        raise ValueError("Motivo da aprovação é obrigatório")
    try:
        inicio = date.fromisoformat(vigencia_inicio)
        fim = date.fromisoformat(vigencia_fim)
    except (TypeError, ValueError):
        raise ValueError("Vigência deve usar datas ISO válidas") from None
    if fim < inicio:
        raise ValueError("Fim da vigência não pode ser anterior ao início")
    with system_conn() as conn:
        antes_row = _ensure_credito(conn, cliente_id, actor_id)
        antes = _snapshot(antes_row)
        solicitacao = conn.execute(
            "SELECT usuario_id FROM credito_evento WHERE cliente_id=? AND tipo_evento='solicitacao' "
            "ORDER BY id DESC LIMIT 1",
            (cliente_id,),
        ).fetchone()
        if solicitacao and solicitacao["usuario_id"] == actor_id:
            raise PermissionError("A aprovação deve ser realizada por responsável diferente do solicitante")
        conn.execute(
            "UPDATE credito_aprovacao SET status='aprovado', limite_aprovado=?, prazo_maximo_dias=?, "
            "condicoes_permitidas=?::jsonb, vigencia_inicio=?, vigencia_fim=?, aprovado_por=?, aprovado_em=NOW(), "
            "bloqueado_por=NULL, bloqueado_em=NULL, motivo_bloqueio=NULL, updated_by=?, updated_at=NOW(), versao=versao+1 WHERE id=?",
            (limite_aprovado, prazo_maximo_dias, json.dumps(condicoes_permitidas or []), inicio, fim, actor_id, actor_id, antes_row["id"]),
        )
        depois = _snapshot(_get_credito(conn, cliente_id, lock=True))
        _registrar_evento(conn, antes, depois, "aprovacao", motivo.strip(), actor_id, ip, correlation_id)
        return depois


def _alterar_status(cliente_id: int, status: str, motivo: str, actor_id: int,
                    ip: str | None, correlation_id: str | None) -> dict:
    _exigir(actor_id, "aprovar")
    if status not in {"bloqueado", "suspenso", "reprovado"}:
        raise ValueError("Status de crédito inválido")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("Motivo é obrigatório")
    with system_conn() as conn:
        antes_row = _ensure_credito(conn, cliente_id, actor_id)
        antes = _snapshot(antes_row)
        conn.execute(
            "UPDATE credito_aprovacao SET status=?, motivo_bloqueio=?, bloqueado_por=?, bloqueado_em=NOW(), "
            "updated_by=?, updated_at=NOW(), versao=versao+1 WHERE id=?",
            (status, motivo, actor_id, actor_id, antes_row["id"]),
        )
        depois = _snapshot(_get_credito(conn, cliente_id, lock=True))
        _registrar_evento(conn, antes, depois, status, motivo, actor_id, ip, correlation_id)
        return depois


def bloquear(cliente_id: int, motivo: str, actor_id: int, ip=None, correlation_id=None) -> dict:
    return _alterar_status(cliente_id, "bloqueado", motivo, actor_id, ip, correlation_id)


def suspender(cliente_id: int, motivo: str, actor_id: int, ip=None, correlation_id=None) -> dict:
    return _alterar_status(cliente_id, "suspenso", motivo, actor_id, ip, correlation_id)


def revisar(cliente_id: int, motivo: str, actor_id: int, ip=None, correlation_id=None) -> dict:
    """Retorna o crédito para análise, sem reativar automaticamente o limite."""
    _exigir(actor_id, "aprovar")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("Motivo é obrigatório")
    with system_conn() as conn:
        antes_row = _ensure_credito(conn, cliente_id, actor_id)
        antes = _snapshot(antes_row)
        conn.execute(
            "UPDATE credito_aprovacao SET status='em_analise', limite_aprovado=0, prazo_maximo_dias=0, "
            "vigencia_inicio=NULL, vigencia_fim=NULL, aprovado_por=NULL, aprovado_em=NULL, "
            "updated_by=?, updated_at=NOW(), versao=versao+1 WHERE id=?",
            (actor_id, antes_row["id"]),
        )
        depois = _snapshot(_get_credito(conn, cliente_id, lock=True))
        _registrar_evento(conn, antes, depois, "revisao", motivo, actor_id, ip, correlation_id)
        return depois


def historico(cliente_id: int, limite: int = 100) -> list[dict]:
    limite = max(1, min(int(limite or 100), 500))
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT ce.*, u.nome AS usuario_nome FROM credito_evento ce "
            "LEFT JOIN usuarios u ON u.id=ce.usuario_id WHERE ce.cliente_id=? ORDER BY ce.id DESC LIMIT ?",
            (cliente_id, limite),
        ).fetchall()
        return [dict(row) for row in rows]


def pendentes(limite: int = 100) -> list[dict]:
    limite = max(1, min(int(limite or 100), 500))
    with system_conn() as conn:
        rows = conn.execute(
            "SELECT ca.*, c.nome AS cliente_nome, c.doc AS cliente_doc FROM credito_aprovacao ca "
            "JOIN clientes c ON c.id=ca.cliente_id WHERE ca.status='em_analise' ORDER BY ca.updated_at, ca.id LIMIT ?",
            (limite,),
        ).fetchall()
        return [dict(row) for row in rows]
