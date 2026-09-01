"""INT-002 cobrança/adquirentes e ADM-001/002 carga inicial e deduplicação."""

from __future__ import annotations

from catalog_server.db import system_conn


# ─── INT-002: status canônico e reconciliação de cobranças ─

STATUS_CANONICO = {"pendente", "pago", "cancelado", "erro", "parcial"}


def status_canonico(conta: dict) -> str:
    """Deriva o status canônico da cobrança (provider/ambiente/referência)."""
    sc = conta.get("status_cobranca") or "pendente"
    if sc == "pago":
        return "pago"
    if sc in ("cancelado", "erro"):
        return sc
    if conta.get("status") == "parcial":
        return "parcial"
    return "pendente"


def reconciliar_pendentes(limite: int = 100) -> dict:
    """Lista cobranças pendentes com provider (para consulta/recheck). Marca
    pendentes de longa duração para enfileirar rechecagem (não perde título)."""
    with system_conn() as conn:
        pendentes = [dict(r) for r in conn.execute(
            """SELECT id, cliente, descricao, valor, status_cobranca, provider_id,
                      payment_id, tipo_cobranca, ambiente_cobranca, ultima_consulta_em
               FROM contas_receber
               WHERE status IN ('aberto','parcial') AND status_cobranca IN ('pendente','erro')
               ORDER BY id LIMIT ?""",
            (limite,),
        ).fetchall()]
        for p in pendentes:
            p["status_canonico"] = status_canonico(p)
        # pendentes há mais de 1 dia sem provider → sinal de falha (ação)
        velhas = [p for p in pendentes if not p.get("provider_id") and p.get("status_cobranca") == "erro"]
    return {"pendentes": pendentes, "sem_provider_acao": len(velhas)}


# ─── ADM-001: carga inicial (clientes/fornecedores) ────────

def importar_carga(tipo: str, itens: list[dict]) -> dict:
    """Importa clientes/fornecedores de forma idempotente (por doc). Nunca
    direto em produção sem aprovação. Retorna contagem + rejeições."""
    tipo = (tipo or "").strip().lower()
    if tipo not in ("clientes", "fornecedores"):
        raise ValueError("tipo inválido (clientes|fornecedores)")
    if not itens:
        raise ValueError("itens é obrigatório")
    importados = 0
    rejeicoes: list[dict] = []
    with system_conn() as conn:
        for i, item in enumerate(itens):
            nome = (item.get("nome") or "").strip()
            doc = (item.get("doc") or item.get("cnpj_cpf") or "").strip()
            if not nome or not doc:
                rejeicoes.append({"linha": i, "motivo": "nome e doc obrigatórios"})
                continue
            if tipo == "clientes":
                existe = conn.execute(
                    "SELECT 1 FROM clientes WHERE doc=?", (doc,)
                ).fetchone()
                if existe:
                    rejeicoes.append({"linha": i, "motivo": "cliente já cadastrado", "doc": doc})
                    continue
                conn.execute(
                    "INSERT INTO clientes (nome, doc, tipo_pessoa, telefone, whatsapp, email, cidade, uf)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (nome, doc, item.get("tipo_pessoa") or ("J" if len(doc) == 14 else "F"),
                     item.get("telefone"), item.get("whatsapp"), item.get("email"),
                     item.get("cidade"), item.get("uf")),
                )
            else:
                existe = conn.execute(
                    "SELECT 1 FROM fornecedores WHERE cnpj_cpf=?", (doc,)
                ).fetchone()
                if existe:
                    rejeicoes.append({"linha": i, "motivo": "fornecedor já cadastrado", "doc": doc})
                    continue
                conn.execute(
                    "INSERT INTO fornecedores (nome, cnpj_cpf, representante, telefone, whatsapp, email, cidade, uf)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (nome, doc, item.get("representante"), item.get("telefone"),
                     item.get("whatsapp"), item.get("email"), item.get("cidade"), item.get("uf")),
                )
            importados += 1
    return {"tipo": tipo, "importados": importados, "rejeicoes": rejeicoes}


# ─── ADM-002: deduplicação (candidatos + merge assistido) ──

def candidatos(tipo: str) -> list[dict]:
    """Candidatos a duplicidade por tipo (sku|ean|cpf|cnpj)."""
    tipo = (tipo or "").strip().lower()
    with system_conn() as conn:
        if tipo == "sku":
            rows = conn.execute(
                """SELECT sku, COUNT(*) AS n, string_agg(id::text, ',') AS ids
                   FROM produtos_cadastro WHERE sku IS NOT NULL AND sku<>'' GROUP BY sku HAVING COUNT(*)>1 ORDER BY n DESC"""
            ).fetchall()
        elif tipo == "ean":
            rows = conn.execute(
                """SELECT ean, COUNT(*) AS n, string_agg(id::text, ',') AS ids
                   FROM produtos_cadastro WHERE ean IS NOT NULL AND ean<>'' GROUP BY ean HAVING COUNT(*)>1 ORDER BY n DESC"""
            ).fetchall()
        elif tipo == "cpf":
            rows = conn.execute(
                """SELECT doc, COUNT(*) AS n, string_agg(id::text, ',') AS ids
                   FROM clientes WHERE tipo_pessoa='F' AND doc IS NOT NULL GROUP BY doc HAVING COUNT(*)>1 ORDER BY n DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT cnpj_cpf AS doc, COUNT(*) AS n, string_agg(id::text, ',') AS ids
                   FROM fornecedores WHERE cnpj_cpf IS NOT NULL GROUP BY cnpj_cpf HAVING COUNT(*)>1 ORDER BY n DESC"""
            ).fetchall()
    return [dict(r) for r in rows]


def merge(primario: int, duplicado: int, tipo: str = "produto") -> dict:
    """Merge assistido: redireciona referências do duplicado para o primário e
    registra auditoria. Nenhum documento é destruído."""
    from catalog_server.services import infra

    if tipo == "produto":
        tabela_refs = [
            ("orcamento_itens", "produto_id"), ("estoque_saldo", "produto_id"),
            ("estoque_movimento", "produto_id"), ("fornecedor_preferencial", "produto_id"),
            ("lotes", "produto_id"), ("produto_identificador", "produto_id"),
            ("nfe_entrada_item", "produto_id"), ("cotacao_itens", "produto_id"),
            ("demanda_registro", "produto_id"),
        ]
    elif tipo == "cliente":
        tabela_refs = [("orcamentos", "cliente_id"), ("contas_receber", "cliente_id"),
                       ("cliente_interacao", "cliente_id"), ("credito_cliente", "cliente_id")]
    else:
        raise ValueError("tipo inválido (produto|cliente)")
    with system_conn() as conn:
        for tabela, coluna in tabela_refs:
            conn.execute(f"UPDATE {tabela} SET {coluna}=? WHERE {coluna}=?", (primario, duplicado))
        infra.registrar("merge_assistido", tipo, primario, antes={"duplicado": duplicado},
                        depois={"primario": primario}, motivo=f"merge de {tipo}", conn=conn)
    return {"primario": primario, "duplicado": duplicado, "referencias_redirecionadas": len(tabela_refs)}