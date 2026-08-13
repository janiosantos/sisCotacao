"""Repositório da matriz de regras fiscais, versões e auditoria.

Módulo Fiscal — modelagem das regras. A resolução por contexto e vigência fica
em `services.fiscal_regras` (que usa este repositório para persistir).
"""
from __future__ import annotations

import json

from catalog_server.db import system_conn

CAMPOS_REGRA = (
    "nome", "descricao", "ativo", "regime", "uf_origem", "uf_destino",
    "tipo_cliente", "contribuinte", "finalidade", "modelo_documento",
    "natureza_operacao", "ncm_prefixo", "cest", "origem",
    "cfop", "cst_icms", "csosn", "cst_pis", "cst_cofins", "cst_ibs", "cst_cbs",
    "modalidade_st", "aliquota_icms", "mva", "base_reducao", "aliquota_icms_st",
    "aliquota_pis", "aliquota_cofins", "aliquota_ibs", "aliquota_cbs",
    "prioridade", "observacao", "dimensao",
)


def _filtra(dados: dict) -> dict:
    return {k: v for k, v in dados.items() if k in CAMPOS_REGRA}


class FiscalRegraRepository:

    def list(self, filtros: dict | None = None) -> list[dict]:
        filtros = filtros or {}
        sql = "SELECT * FROM fiscal_regra WHERE 1=1"
        args: list = []
        for campo in ("regime", "uf_destino", "tipo_cliente", "contribuinte", "finalidade", "modelo_documento", "dimensao"):
            if filtros.get(campo):
                sql += f" AND {campo}=?"
                args.append(filtros[campo])
        if filtros.get("ncm"):
            sql += " AND (ncm_prefixo='' OR ? LIKE ncm_prefixo || '%')"
            args.append(filtros["ncm"])
        if filtros.get("somente_ativos"):
            sql += " AND ativo=1"
        sql += " ORDER BY prioridade, nome"
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def get(self, regra_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM fiscal_regra WHERE id=?", (regra_id,)).fetchone()
            return dict(row) if row else None

    def create(self, dados: dict, usuario_id: int | None = None, motivo: str = "") -> int:
        dados = _filtra(dados)
        dados.setdefault("prioridade", 100)
        cols = ", ".join(dados.keys())
        ph = ", ".join("?" for _ in dados)
        with system_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO fiscal_regra ({cols}) VALUES ({ph})", list(dados.values())
            )
            rid = cur.lastrowid
            conn.execute(
                "INSERT INTO fiscal_regra_auditoria"
                " (regra_id, acao, usuario_id, valor_novo, motivo) VALUES (?,?,?,?,?)",
                (rid, "criada", usuario_id, json.dumps(dados, ensure_ascii=False), motivo),
            )
            return rid

    def update(self, regra_id: int, dados: dict, usuario_id: int | None = None, motivo: str = "") -> bool:
        dados = _filtra(dados)
        if not dados:
            return False
        with system_conn() as conn:
            atual = conn.execute("SELECT * FROM fiscal_regra WHERE id=?", (regra_id,)).fetchone()
            if atual is None:
                return False
            sets = ", ".join(f"{k}=?" for k in dados)
            conn.execute(
                f"UPDATE fiscal_regra SET {sets}, atualizado_em=datetime('now') WHERE id=?",
                list(dados.values()) + [regra_id],
            )
            conn.execute(
                "INSERT INTO fiscal_regra_auditoria"
                " (regra_id, acao, usuario_id, valor_anterior, valor_novo, motivo)"
                " VALUES (?,?,?,?,?,?)",
                (
                    regra_id, "alterada", usuario_id,
                    json.dumps(dict(atual), ensure_ascii=False),
                    json.dumps({**dict(atual), **dados}, ensure_ascii=False),
                    motivo,
                ),
            )
            return True

    def set_ativo(self, regra_id: int, ativo: bool, usuario_id: int | None = None, motivo: str = "") -> bool:
        with system_conn() as conn:
            atual = conn.execute("SELECT * FROM fiscal_regra WHERE id=?", (regra_id,)).fetchone()
            if atual is None:
                return False
            conn.execute("UPDATE fiscal_regra SET ativo=?, atualizado_em=datetime('now') WHERE id=?",
                         (int(ativo), regra_id))
            conn.execute(
                "INSERT INTO fiscal_regra_auditoria (regra_id, acao, usuario_id, valor_anterior, valor_novo, motivo)"
                " VALUES (?,?,?,?,?,?)",
                (regra_id, "ativada" if ativo else "desativada", usuario_id,
                 json.dumps({"ativo": atual["ativo"]}, ensure_ascii=False),
                 json.dumps({"ativo": int(ativo)}, ensure_ascii=False), motivo),
            )
            return True

    def list_auditoria(self, regra_id: int | None = None, limit: int = 200) -> list[dict]:
        sql = (
            "SELECT a.*, u.nome AS usuario_nome, r.nome AS regra_nome"
            " FROM fiscal_regra_auditoria a"
            " LEFT JOIN usuarios u ON u.id=a.usuario_id"
            " LEFT JOIN fiscal_regra r ON r.id=a.regra_id"
        )
        args: list = []
        if regra_id:
            sql += " WHERE a.regra_id=?"
            args.append(regra_id)
        sql += " ORDER BY a.id DESC LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]


class FiscalRegraVersaoRepository:

    def list(self, regra_id: int) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM fiscal_regra_versao WHERE regra_id=? ORDER BY data_inicio DESC",
                (regra_id,),
            ).fetchall()]

    def get(self, versao_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM fiscal_regra_versao WHERE id=?", (versao_id,)).fetchone()
            return dict(row) if row else None

    def create(
        self,
        regra_id: int,
        versao: str,
        fonte: str,
        data_inicio: str,
        data_fim: str | None = None,
        parametros: dict | None = None,
    ) -> int:
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fiscal_regra_versao (regra_id, versao, fonte, data_inicio, data_fim, parametros)"
                " VALUES (?,?,?,?,?,?)",
                (regra_id, versao, fonte, data_inicio, data_fim,
                 json.dumps(parametros or {}, ensure_ascii=False)),
            )
            return cur.lastrowid

    def set_status(self, versao_id: int, status: str, usuario_id: int | None = None, motivo: str = "") -> bool:
        if status not in ("ativa", "inativa", "rascunho"):
            return False
        with system_conn() as conn:
            v = conn.execute("SELECT * FROM fiscal_regra_versao WHERE id=?", (versao_id,)).fetchone()
            if v is None:
                return False
            conn.execute("UPDATE fiscal_regra_versao SET status=? WHERE id=?", (status, versao_id))
            conn.execute(
                "INSERT INTO fiscal_regra_auditoria"
                " (regra_id, acao, usuario_id, valor_anterior, valor_novo, motivo, fonte,"
                "  vigencia_inicio, vigencia_fim)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (v["regra_id"], "versao", usuario_id,
                 json.dumps({"status": v["status"]}, ensure_ascii=False),
                 json.dumps({"status": status}, ensure_ascii=False), motivo, v["fonte"],
                 v["data_inicio"], v["data_fim"]),
            )
            return True


fiscal_regra_repo = FiscalRegraRepository()
fiscal_regra_versao_repo = FiscalRegraVersaoRepository()
