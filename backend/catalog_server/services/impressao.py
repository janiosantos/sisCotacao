"""Retaguarda de impressão (PDV).

Gera cupom ESC/POS a partir do orçamento e o entrega a um *driver* de
impressão escolhido em `impressao_config.driver`. O envio é independente do
documento: o cupom é sempre montado em bytes ESC/POS e cada driver cuida do
transporte (rede TCP, arquivo, futuramente USB/Windows/HTTP), permitindo
usar qualquer impressora sem alterar o restante do sistema.

Drivers disponíveis (registry `_DRIVERS`):
  - `escpos_tcp` : envia via socket TCP para host:porta (impressora de rede /
                    emulador 127.0.0.1:9100). Em Docker, o host 127.0.0.1 é
                    redirecionado automaticamente para o host da máquina
                    (host.docker.internal).
  - `arquivo`    : grava os bytes em um arquivo (IMPRESSAO_ARQUIVO ou
                    ./cupom_impresso.bin) — útil para depuração sem impressora.

A fila em `impressao_fila` é processada por um worker em thread: o sistema
fica aguardando e drenando trabalhos sem interação — ao clicar em Imprimir o
cupom vai direto ao driver, sem diálogo de impressora.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

from catalog_server.db import system_conn

# ---------------------------------------------------------------------------
# Builder ESC/POS
# ---------------------------------------------------------------------------

_INIT = b"\x1b\x40"
_ALIGN_CENTER = b"\x1b\x61\x01"
_ALIGN_LEFT = b"\x1b\x61\x00"
_FONT_BIG = b"\x1b\x21\x30"
_FONT_NORMAL = b"\x1b\x21\x00"
_BOLD_ON = b"\x1b\x45\x01"
_BOLD_OFF = b"\x1b\x45\x00"
_REVERSE_ON = b"\x1b\x42\x01"
_REVERSE_OFF = b"\x1b\x42\x00"
_FEED3 = b"\x1b\x64\x03"
_CUT = b"\x1d\x56\x42\x00"


def _cols(papel_mm: int) -> int:
    return 42 if papel_mm >= 80 else 30


def _enc(texto: str) -> bytes:
    return str(texto).encode("cp850", "replace")


def _linha_esquerda_direita(esq: str, dir_: str, cols: int) -> bytes:
    esp = max(1, cols - len(esq) - len(dir_))
    return _enc(esq + " " * esp + dir_ + "\n")


def _separador(char: str, cols: int) -> bytes:
    return _enc(char * cols + "\n")


def orcamento_para_escpos(orc: dict, papel_mm: int = 80) -> bytes:
    cols = _cols(papel_mm)
    out = bytearray()
    out += _INIT
    out += _ALIGN_CENTER + _FONT_BIG + _enc("COTAÇÕES\n")
    out += _FONT_NORMAL + _enc("ORÇAMENTO " + (orc.get("numero") or "") + "\n")
    out += _ALIGN_LEFT
    out += _separador("=", cols)

    out += _enc("Cliente: " + (orc.get("cliente") or "—") + "\n")
    contato = orc.get("contato") or ""
    if contato:
        out += _enc("Contato: " + contato + "\n")
    criado = (orc.get("criado_em") or "")[:16]
    if criado:
        out += _enc("Data: " + criado + "\n")
    out += _separador("-", cols)

    for it in orc.get("itens") or []:
        qtd = float(it.get("quantidade") or 1)
        nome = it.get("nome") or "Item"
        sub = float(it.get("subtotal") or float(it.get("preco_unitario") or 0) * qtd)
        out += _linha_esquerda_direita(f"{qtd:g}x {nome}", f"R$ {sub:.2f}", cols)
        extra = " · ".join(
            x for x in (it.get("sku") or "", it.get("marca") or "", it.get("especificacao") or "") if x
        )
        if extra:
            out += _enc("   " + extra[: cols - 3] + "\n")

    out += _separador("-", cols)
    out += _linha_esquerda_direita("Subtotal", f"R$ {orc.get('subtotal') or 0:.2f}", cols)
    out += _linha_esquerda_direita("Desconto", f"R$ {orc.get('desconto') or 0:.2f}", cols)
    out += _REVERSE_ON + _linha_esquerda_direita("TOTAL", f"R$ {orc.get('total') or 0:.2f}", cols) + _REVERSE_OFF

    obs = orc.get("observacoes") or ""
    if obs:
        out += _separador("-", cols) + _enc(obs + "\n")

    out += _FEED3
    out += _CUT
    return bytes(out)


# ---------------------------------------------------------------------------
# Drivers de impressão (transporte)
# ---------------------------------------------------------------------------

def _host_destino(host: str) -> str:
    """Resolve o host para onde o bytecode deve ser enviado.

    Quando o backend roda em Docker e o usuário configurou o loopback
    (127.0.0.1/localhost) — que dentro do container aponta para o próprio
    container — redireciona para o host da máquina (host.docker.internal),
    onde normalmente está a impressora/emulador.
    """
    if host in ("", "127.0.0.1", "localhost") and Path("/.dockerenv").exists():
        return "host.docker.internal"
    return host


class DriverImpressao:
    """Contrato dos drivers de transporte de impressão.

    Um driver recebe a configuração salva (`cfg`) e os bytes ESC/POS do
    documento (`dados`) e cuida da entrega física. Para suportar uma nova
    impressora, basta criar uma subclasse, registrá-la em `_DRIVERS` e
    escolhê-la na tela de configuração — nada no restante do sistema muda.
    """

    name = "base"
    label = "Base"
    usa_host = True

    def imprimir(self, cfg: dict, dados: bytes) -> None:  # pragma: no cover
        raise NotImplementedError


class DriverEscposTcp(DriverImpressao):
    name = "escpos_tcp"
    label = "ESC/POS via rede (TCP) — impressora ou emulador na porta 9100"
    usa_host = True

    def imprimir(self, cfg: dict, dados: bytes) -> None:
        host = _host_destino(str(cfg.get("host") or "127.0.0.1"))
        porta = int(cfg.get("porta") or 9100)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(6)
                s.connect((host, porta))
                s.sendall(dados)
        except OSError as exc:
            raise ConnectionError(
                f"Não foi possível conectar à impressora {host}:{porta} "
                f"(verifique se o emulador/impressora está ativo). {exc}"
            ) from exc


class DriverArquivo(DriverImpressao):
    """Grava o bytecode em um arquivo (depuração sem impressora).

    Caminho: env `IMPRESSAO_ARQUIVO` ou `./cupom_impresso.bin`.
    """

    name = "arquivo"
    label = "Arquivo (grava o cupom em binário — para teste)"
    usa_host = False

    def imprimir(self, cfg: dict, dados: bytes) -> None:
        caminho = os.environ.get("IMPRESSAO_ARQUIVO", "./cupom_impresso.bin")
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "wb") as f:
            f.write(dados)


_DRIVERS: dict[str, DriverImpressao] = {
    d.name: d for d in (DriverEscposTcp(), DriverArquivo())
}


def driver_por_nome(nome: str | None) -> DriverImpressao:
    return _DRIVERS.get(nome or "") or _DRIVERS["escpos_tcp"]


class ImpressaoService:
    """Config singleton + fila de trabalhos processada em thread."""

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORTA = 9100
    DEFAULT_PAPEL = 80
    DEFAULT_DRIVER = "escpos_tcp"

    def __init__(self) -> None:
        self._worker: threading.Thread | None = None
        self._rodando = True

    # ------------------------------------------------------------------

    def config(self) -> dict[str, Any]:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT driver, host, porta, papel_mm, auto_impressao, ativo FROM impressao_config WHERE id=1"
            ).fetchone()
        if row is None:
            return {
                "driver": self.DEFAULT_DRIVER,
                "host": self.DEFAULT_HOST,
                "porta": self.DEFAULT_PORTA,
                "papel_mm": self.DEFAULT_PAPEL,
                "auto_impressao": 0,
                "ativo": 1,
            }
        return dict(row)

    def salvar_config(self, cfg: dict) -> None:
        driver = str(cfg.get("driver") or self.DEFAULT_DRIVER)
        host = str(cfg.get("host") or self.DEFAULT_HOST)
        porta = int(cfg.get("porta") or self.DEFAULT_PORTA)
        papel = int(cfg.get("papel_mm") or self.DEFAULT_PAPEL)
        auto = 1 if cfg.get("auto_impressao") else 0
        ativo = 1 if cfg.get("ativo", True) else 0
        with system_conn() as conn:
            conn.execute(
                """
                INSERT INTO impressao_config (id, driver, host, porta, papel_mm, auto_impressao, ativo, atualizado_em)
                VALUES (1,?,?,?,?,?,?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    driver=excluded.driver, host=excluded.host, porta=excluded.porta, papel_mm=excluded.papel_mm,
                    auto_impressao=excluded.auto_impressao, ativo=excluded.ativo,
                    atualizado_em=datetime('now')
                """,
                (driver, host, porta, papel, auto, ativo),
            )

    # ------------------------------------------------------------------

    def enfileirar(self, orc: dict) -> int:
        """Serializa o orçamento na fila e devolve o id do job."""
        payload = json.dumps(orc, ensure_ascii=False, default=str)
        with system_conn() as conn:
            cur = conn.execute(
                "INSERT INTO impressao_fila (tipo, referencia, payload) VALUES ('orcamento', ?, ?)",
                (orc.get("numero") or "", payload),
            )
            return cur.lastrowid

    def status(self) -> list[dict]:
        with system_conn() as conn:
            rows = conn.execute(
                "SELECT id, tipo, referencia, status, erro, criado_em, processado_em "
                "FROM impressao_fila ORDER BY id DESC LIMIT 20"
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------

    def _drenar_fila(self) -> None:
        while self._rodando:
            job = self._pegar_pendente()
            if job is None:
                time.sleep(0.5)
                continue
            try:
                orc = json.loads(job["payload"])
                self._imprimir_agora(orc)
                self._marcar(job["id"], "ok", None)
            except Exception as exc:  # noqa: BLE001
                self._marcar(job["id"], "erro", str(exc))

    def _pegar_pendente(self) -> dict | None:
        with system_conn() as conn:
            row = conn.execute(
                "SELECT * FROM impressao_fila WHERE status='pendente' ORDER BY id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            conn.execute("UPDATE impressao_fila SET status='processando' WHERE id=?", (row["id"],))
            return dict(row)

    def _marcar(self, job_id: int, status: str, erro: str | None) -> None:
        with system_conn() as conn:
            conn.execute(
                "UPDATE impressao_fila SET status=?, erro=?, processado_em=datetime('now') WHERE id=?",
                (status, erro, job_id),
            )

    def _imprimir_agora(self, orc: dict) -> None:
        """Entrega o cupom ESC/POS ao driver de impressão configurado."""
        cfg = self.config()
        if not cfg["ativo"]:
            return
        dados = orcamento_para_escpos(orc, papel_mm=int(cfg["papel_mm"]))
        driver_por_nome(cfg.get("driver")).imprimir(cfg, dados)

    # ------------------------------------------------------------------

    def start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._drenar_fila, daemon=True)
        self._worker.start()


impressao_service = ImpressaoService()