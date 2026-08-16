"""Rastreio de documentos fiscais (NFC-e/NF-e) e config da integração Tecnospeed."""
from __future__ import annotations

import json

from catalog_server.db import system_conn


class TecnospeedConfigRepository:

    def get_all(self) -> dict:
        with system_conn() as conn:
            rows = conn.execute("SELECT chave, valor FROM tecnospeed_config").fetchall()
        return {r["chave"]: r["valor"] for r in rows}

    def set(self, chaves: dict) -> dict:
        with system_conn() as conn:
            for chave, valor in chaves.items():
                conn.execute(
                    "INSERT INTO tecnospeed_config (chave, valor, atualizado_em)"
                    " VALUES (?,?,datetime('now'))"
                    " ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=excluded.atualizado_em",
                    (chave, str(valor)),
                )
        return self.get_all()

    def simulado(self) -> bool:
        return self.get_all().get("simulado", "1") == "1"

    def ambiente(self) -> str:
        return self.get_all().get("ambiente", "homologacao")


class DocumentoFiscalRepository:

    def get_by_orcamento(self, orcamento_id: int, modelo: str = "65") -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM documentos_fiscais WHERE orcamento_id=? AND modelo=?",
                (orcamento_id, modelo),
            ).fetchone()
            return dict(row) if row else None

    def get(self, doc_id: int) -> dict | None:
        with system_conn() as conn:
            row = conn.execute("SELECT * FROM documentos_fiscais WHERE id=?", (doc_id,)).fetchone()
            return dict(row) if row else None

    def get_by_tecnospeed_id(self, tecnospeed_id: str) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM documentos_fiscais WHERE tecnospeed_id=?", (tecnospeed_id,)
            ).fetchone()
            return dict(row) if row else None

    def criar_ou_reiniciar(
        self, orcamento_id: int, modelo: str, ambiente: str, payload: dict
    ) -> int:
        """Cria a linha de rastreio (ou reinicia, se a última tentativa não
        vingou — rejeitada/erro) e volta pra status 'pendente'."""
        with system_conn() as conn:
            existente = conn.execute(
                "SELECT id, status FROM documentos_fiscais WHERE orcamento_id=? AND modelo=?",
                (orcamento_id, modelo),
            ).fetchone()
            if existente:
                conn.execute(
                    "UPDATE documentos_fiscais SET status='pendente', ambiente=?,"
                    " motivo=NULL, payload_enviado=?, atualizado_em=datetime('now')"
                    " WHERE id=?",
                    (ambiente, json.dumps(payload, ensure_ascii=False), existente["id"]),
                )
                return existente["id"]
            cur = conn.execute(
                "INSERT INTO documentos_fiscais (orcamento_id, modelo, ambiente, status, payload_enviado)"
                " VALUES (?,?,?, 'pendente', ?)",
                (orcamento_id, modelo, ambiente, json.dumps(payload, ensure_ascii=False)),
            )
            return cur.lastrowid

    def atualizar(self, doc_id: int, **campos) -> bool:
        permitidos = {
            "status", "tecnospeed_id", "chave_acesso", "protocolo", "numero",
            "serie", "motivo", "xml_url", "danfe_url", "resposta_bruta",
        }
        sets, vals = [], []
        for k, v in campos.items():
            if k in permitidos:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return False
        sets.append("atualizado_em=datetime('now')")
        vals.append(doc_id)
        with system_conn() as conn:
            cur = conn.execute(
                f"UPDATE documentos_fiscais SET {', '.join(sets)} WHERE id=?", vals
            )
            return cur.rowcount > 0


tecnospeed_config_repo = TecnospeedConfigRepository()
documento_fiscal_repo = DocumentoFiscalRepository()
